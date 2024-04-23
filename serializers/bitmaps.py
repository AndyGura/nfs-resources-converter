from typing import Any

from PIL import Image

from library.exceptions import SerializationException
from resources.eac.bitmaps import Bitmap4Bit
from resources.eac.utils import determine_palette_for_8_bit_bitmap
from serializers import BaseFileSerializer
from serializers.misc.path_utils import escape_chars


class BitmapSerializer(BaseFileSerializer):

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs):
        super().serialize(data, path, id=id, block=block)
        bitmap = data['bitmap']
        if isinstance(block, Bitmap4Bit):
            bitmap = [item for row in bitmap for item in row]
        Image.frombytes('RGBA',
                        (data['width'], data['height']),
                        bytes().join([c.to_bytes(4, 'big') for c in bitmap])).save(f'{escape_chars(path)}.png')

    def deserialize(self, path: str, id=None, block=None, **kwargs):
        image = Image.open(path + '.png')
        image_rgba = image.convert("RGBA")
        data = block.new_data()
        data['width'] = image.width
        data['height'] = image.height
        bitmap = [(x[0] << 24) | (x[1] << 16) | (x[2] << 8) | x[3] for x in list(image_rgba.getdata())]
        if isinstance(block, Bitmap4Bit):
            bitmap = [bitmap[i:i + image.width] for i in range(0, len(bitmap), image.width)]
        data['bitmap'] = bitmap
        return data


class BitmapWithPaletteSerializer(BaseFileSerializer):

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs):
        super().serialize(data, path, id=id, block=block)
        (palette_block, palette_data) = determine_palette_for_8_bit_bitmap(block, data, id)
        if palette_block is None:
            raise SerializationException('Palette not found for 8bit bitmap')
        colors = []
        palette_colors = [c for c in palette_data['colors']]
        if palette_data['last_color_transparent']:
            palette_colors[255] = 0
        for index in data['bitmap']:
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
