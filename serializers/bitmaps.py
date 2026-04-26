from PIL import Image

from resources.eac.utils import determine_palette_for_8_bit_bitmap
from serializers import BaseFileSerializer
from serializers.misc.path_utils import escape_chars


class BitmapSerializer(BaseFileSerializer):

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs):
        if data['resource_id'].startswith('8Bit'):
            return BitmapWithPaletteSerializer().serialize(data, path, id=id, block=block, **kwargs)
        super().serialize(data, path, id=id, block=block)
        if data['resource_id'].startswith('4Bit'):
            bitmap = [item for row in data['bitmap']['data'] for item in row]
        else:
            bitmap = data['bitmap']['data']
        Image.frombytes('RGBA',
                        (data['width'], data['height']),
                        bytes().join([c.to_bytes(4, 'big') for c in bitmap])).save(f'{escape_chars(path)}.png')

    def deserialize(self, path: str, id=None, block=None, **kwargs):
        # TODO
        # if data['resource_id'].startswith('8Bit'):
        #     return BitmapWithPaletteSerializer().serialize(data, path, id=id, block=block, **kwargs)
        image = Image.open(path + '.png')
        image_rgba = image.convert("RGBA")
        data = block.new_data()
        data['width'] = image.width
        data['height'] = image.height
        bitmap = [(x[0] << 24) | (x[1] << 16) | (x[2] << 8) | x[3] for x in list(image_rgba.getdata())]
        if data['resource_id'].startswith('4Bit'):
            data['bitmap']['data'] = [bitmap[i:i + image.width] for i in range(0, len(bitmap), image.width)]
        else:
            data['bitmap']['data'] = bitmap
        return data


class PaletteSerializer(BaseFileSerializer):

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs):
        super().serialize(data, path, id=id, block=block)
        with open(f'{path}.pal.txt', 'w') as f:
            f.write(f'{block.__class__.__name__}\n')
            for i, color in enumerate(data['colors']['data']):
                f.write(f'\n{hex(i)}:\t#{hex(color)}')
            f.write('\n')


class BitmapWithPaletteSerializer(BaseFileSerializer):

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs):
        super().serialize(data, path, id=id, block=block)
        (palette_block, palette_data) = determine_palette_for_8_bit_bitmap(block, data, id)
        colors = []
        palette_colors = []
        if palette_block is None:
            for i in range(256):
                palette_colors.append(0xffffff00 | i)
        else:
            palette_colors = [c for c in palette_data['colors']['data']]
            if palette_data['last_color_transparent']:
                palette_colors[255] = 0
        for index in data['bitmap']['data']:
            try:
                colors.append(palette_colors[index])
            except IndexError:
                colors.append(0)
        Image.frombytes('RGBA',
                        (data['width'], data['height']),
                        bytes().join([c.to_bytes(4, 'big') for c in colors])).save(f'{escape_chars(path)}.png')

    def deserialize(self, path: str, id=None, block=None, palette=None, **kwargs):
        source = Image.open(path)
        transparency = palette[255]
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
        data = block.new_data()
        data['width'] = im.width
        data['height'] = im.height
        data['bitmap'] = list(im.getdata())
        return data
