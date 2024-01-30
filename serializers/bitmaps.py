from PIL import Image

from library.helpers.exceptions import SerializationException
from library.read_data import ReadData
from resources.eac.bitmaps import Bitmap8Bit
from resources.utils import determine_palette_for_8_bit_bitmap
from serializers import BaseFileSerializer
from serializers.misc.path_utils import escape_chars


class BitmapSerializer(BaseFileSerializer):

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs):
        super().serialize(data, path, id=id, block=block)
        Image.frombytes('RGBA',
                        (data['width'], data['height']),
                        bytes().join([c.to_bytes(4, 'big') for c in data['bitmap']])).save(f'{escape_chars(path)}.png')

    def deserialize(self, path: str, resource: ReadData, **kwargs) -> None:
        image = Image.open(path + '.png')
        image_rgba = image.convert("RGBA")
        resource['width'] = image.width
        resource['height'] = image.height
        resource['bitmap'] = [(x[0] << 24) | (x[1] << 16) | (x[2] << 8) | x[3] for x in list(image_rgba.getdata())]


class BitmapWithPaletteSerializer(BaseFileSerializer):

    @staticmethod
    def has_tail_lights(id: str):
        return '.CFM' in id and id.split('/')[-2] in ['rsid', 'lite']

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs):
        super().serialize(data, path, id=id, block=block)
        (palette_block, palette_data) = determine_palette_for_8_bit_bitmap(block, data, id)
        if palette_block is None:
            raise SerializationException('Palette not found for 8bit bitmap')
        colors = []
        palette_colors = [c for c in palette_data['colors']]
        if palette_data['last_color_transparent']:
            palette_colors[255] = 0
        if self.has_tail_lights(id):
            # NFS1 car tail lights: make transparent
            try:
                palette_colors[254] = 0
            except IndexError:
                print('WARN: car tail lights problem: palette is too short')
                pass
        for index in data['bitmap']:
            try:
                colors.append(palette_colors[index])
            except IndexError:
                colors.append(0)
        Image.frombytes('RGBA',
                        (data['width'], data['height']),
                        bytes().join([c.to_bytes(4, 'big') for c in colors])).save(f'{escape_chars(path)}.png')

    def deserialize(self, path: str, resource: ReadData[Bitmap8Bit], palette=None, **kwargs) -> None:
        source = Image.open(escape_chars(path) + '.png')
        transparency = palette[254] if self.has_tail_lights(resource) else palette[255]
        im = Image.new("RGB", source.size, ((transparency & 0xff000000) >> 24,
                                            (transparency & 0xff0000) >> 16,
                                            (transparency & 0xff00) >> 8))
        im.paste(source, (None if source.mode == 'RGB' else source.split()[3]))
        palette_bytes = bytearray()
        for color in palette:
            red = (color >> 24) & 0xFF
            green = (color >> 16) & 0xFF
            blue = (color >> 8) & 0xFF
            palette_bytes.extend([red, green, blue])
        palette_image = Image.new("P", (1, 1))
        palette_image.putpalette(palette_bytes)
        im = im.quantize(len(palette_bytes), palette=palette_image)
        # palette_colors = [(r << 24) | (g << 16) | (b << 8) | 0xff for (r, g, b) in im.palette.colors.keys()]
        # TODO handle transparency
        # if 0xFF00FF00 in palette_colors:
        #     # make it last
        #     palette_colors.remove(0xFF00FF00)
        #     palette_colors += [0xFF00FF00]
        resource.value.block_size.value = 16 + im.width * im.height
        resource.value.width.value = im.width
        resource.value.height.value = im.height
        resource.value.bitmap.value = list(im.getdata())
        if resource.value.trailing_bytes:
            resource.value.trailing_bytes.value = []
        # TODO rewrite code below for new library
        # TODO wow, it's so complicated... Need a way to construct a new resource easily
        # block = Palette24BitDos()
        # resource.value.palette = ReadData(block=block,
        #                                   block_state={'id': resource.id + '/palette'},
        #                                   value=DataWrapper({
        #                                       'resource_id': ReadData(value=0x22,
        #                                                               block=block.instance_fields_map['resource_id'],
        #                                                               block_state={ 'id': resource.id + '/palette/resource_id' }),
        #                                       'unknowns': ReadData(value=[0] * 15,
        #                                                            block=block.instance_fields_map['unknowns'],
        #                                                            block_state={ 'id': resource.id + '/palette/unknowns' }),
        #                                       'colors': ReadData(value=[ReadData(value=x,
        #                                                                          block_state={ 'id': resource.id + '/palette/colors/' + str(i) },
        #                                                                          block=block.instance_fields_map['colors'].child,
        #                                                                          ) for i, x in enumerate(palette_colors)],
        #                                                          block=block.instance_fields_map['colors'],
        #                                                          block_state={
        #                                                              'id': resource.id + '/palette/colors'
        #                                                          }),
        #                                   }))
        # TODO if single image in SHPI, should change this SHPI !pal resource probably
        # from library import require_resource
        # shpi, _ = require_resource(resource.id[:max(resource.id.rfind('__children'), resource.id.rfind('/children'))])
        # palette = next(x for x in shpi.children if x.id[-4:] in ['!pal', '!PAL'])
        # if len(palette_colors) < 256:
        #     palette_colors += [0] * (256 - len(palette_colors))
        # palette.value.colors.value = [ReadData(value=x,
        #                                        block_state={'id': resource.id + '/palette/colors/' + str(i)},
        #                                        block=palette.block.instance_fields_map['colors'].child,
        #                                        ) for i, x in enumerate(palette_colors)]
