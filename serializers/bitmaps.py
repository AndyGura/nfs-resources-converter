from PIL import Image

from library.helpers.exceptions import SerializationException
from library.read_data import ReadData
from resources.eac.bitmaps import AnyBitmapBlock, Bitmap8Bit
from resources.utils import determine_palette_for_8_bit_bitmap
from serializers import BaseFileSerializer


class BitmapSerializer(BaseFileSerializer):

    def serialize(self, data: ReadData[AnyBitmapBlock], path: str):
        super().serialize(data, path)
        Image.frombytes('RGBA',
                        (data.width.value, data.height.value),
                        bytes().join([c.to_bytes(4, 'big') for c in data.bitmap])).save(f'{path}.png')


class BitmapWithPaletteSerializer(BaseFileSerializer):

    @staticmethod
    def has_tail_lights(data: ReadData[Bitmap8Bit]):
        return data.id[-4:] in ['rsid', 'lite'] and '.CFM' in data.id

    def serialize(self, data: ReadData[Bitmap8Bit], path: str):
        super().serialize(data, path)
        palette = determine_palette_for_8_bit_bitmap(data)
        if palette is None:
            raise SerializationException('Palette not found for 8bit bitmap')
        colors = []
        palette_colors = [c.value for c in palette.colors]
        if getattr(palette, 'last_color_transparent', False):
            palette_colors[255] = 0
        if self.has_tail_lights(data):
            # NFS1 car tail lights: make transparent
            try:
                palette_colors[254] = 0
            except IndexError:
                print('WARN: car tail lights problem: palette is too short')
                pass
        for index in data.bitmap:
            try:
                colors.append(palette_colors[index])
            except IndexError:
                colors.append(0)
        Image.frombytes('RGBA',
                        (data.width.value, data.height.value),
                        bytes().join([c.to_bytes(4, 'big') for c in colors])).save(f'{path}.png')
        if self.settings.images__save_inline_palettes and data.value.palette and data.value.palette == palette:
            from serializers import PaletteSerializer
            palette_serializer = PaletteSerializer()
            palette_serializer.serialize(data.palette, f'{path}_pal')

    def deserialize(self, path: str, resource: ReadData[Bitmap8Bit], palette=None, **kwargs) -> None:
        source = Image.open(path + '.png')
        im = Image.new("RGB", source.size, (255, 0, 255))
        im.paste(source, mask=source.split()[3])
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
