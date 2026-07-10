from typing import List

from PIL import Image

from resources.eac.utils import determine_palette_for_8_bit_bitmap
from serializers import BaseFileSerializer
from serializers.misc.path_utils import escape_chars


class ImageSerializer(BaseFileSerializer):

    def ui_serialization(self):
        return {
            'file_type': 'png',
            'is_directory': False,
            'output_file_name_suffix': '.png',
            'reversible': True,
            'reversible_settings_patch': {}
        }

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs) -> List[str]:
        if data['resource_id'].startswith('8Bit'):
            return BitmapWithPaletteSerializer().serialize(data, path, id=id, block=block, **kwargs)
        super().serialize(data, path, id=id, block=block)
        if data['resource_id'].startswith('4Bit'):
            bitmap = [item for row in data['bitmap'] for item in row]
        else:
            bitmap = data['bitmap']
        file_path = escape_chars(path)
        if not file_path.endswith('.png'):
            file_path += '.png'
        Image.frombytes('RGBA',
                        (data['width'], data['height']),
                        bytes().join([c.to_bytes(4, 'big') for c in bitmap])).save(file_path)
        return [file_path]

    def deserialize(self, file_paths: List[str], id=None, block=None, **kwargs):
        # TODO make it differently
        # if data['resource_id'].startswith('8Bit'):
        #     return BitmapWithPaletteSerializer().serialize(data, path, id=id, block=block, **kwargs)
        if len(file_paths) == 0:
            raise Exception('No image file provided to ImageSerializer')
        if len(file_paths) != 1:
            raise Exception('ImageSerializer can only deserialize one file at once')
        image = Image.open(file_paths[0])
        image_rgba = image.convert("RGBA")
        data = block.new_data()
        data['resource_id'] = '32Bit color format bitmap'
        data['width'] = image.width
        data['height'] = image.height
        bitmap = [(x[0] << 24) | (x[1] << 16) | (x[2] << 8) | x[3] for x in list(image_rgba.getdata())]
        data['bitmap'] = bitmap
        # if data['resource_id'].startswith('4Bit'):
        #     data['bitmap'] = [bitmap[i:i + image.width] for i in range(0, len(bitmap), image.width)]
        # else:
        #     data['bitmap'] = bitmap
        return data


class PaletteSerializer(BaseFileSerializer):

    def ui_serialization(self):
        return {
            'file_type': 'txt',
            'is_directory': False,
            'output_file_name_suffix': '.pal.txt',
            'reversible': True,
            'reversible_settings_patch': {}
        }

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs) -> List[str]:
        if not path.endswith('.pal.txt'):
            path += '.pal.txt'
        super().serialize(data, path, id=id, block=block)
        with open(path, 'w') as f:
            f.write(f'{block.__class__.__name__}\n')
            f.write(f'Color model: {data["resource_id"]}\n')
            for i, color in enumerate(data['colors']['data']):
                f.write(f'\n{hex(i)}:\t#{hex(color)}')
            f.write('\n')
        return [path]

    def deserialize(self, file_paths: List[str], id=None, block=None, **kwargs):
        data = block.new_data()
        colors = []
        if len(file_paths) != 1:
            raise Exception('PaletteSerializer can only deserialize one file at once')
        with open(file_paths[0], 'r') as f:
            lines = f.readlines()
            if len(lines) > 1 and lines[1].startswith('Color model: '):
                new_resource_id = lines[1].strip().replace('Color model: ', '')
                if new_resource_id not in block.field_blocks_map['resource_id'].enum_name_map:
                    raise Exception(f'Invalid palette file format, unknown color model: "{new_resource_id}"')
            else:
                raise Exception('Invalid palette file format, missing color model line')
            try:
                for line in lines[1:]:
                    line = line.strip()
                    if line and ':' in line:
                        parts = line.split(':\t#')
                        if len(parts) == 2:
                            color_hex = parts[1].strip()
                            color = int(color_hex, 16)
                            colors.append(color)
            except Exception as e:
                raise Exception(f'Error while parsing palette file: {e}')

        data['resource_id'] = new_resource_id
        data['colors']['data'] = colors
        return data
    

class BitmapWithPaletteSerializer(BaseFileSerializer):

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs) -> List[str]:
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
        for index in data['bitmap']:
            try:
                colors.append(palette_colors[index])
            except IndexError:
                colors.append(0)
        file_path = escape_chars(path)
        if not file_path.endswith('.png'):
            file_path += '.png'
        Image.frombytes('RGBA',
                        (data['width'], data['height']),
                        bytes().join([c.to_bytes(4, 'big') for c in colors])).save(file_path)
        return [file_path]

    def deserialize(self, file_paths: List[str], id=None, block=None, palette=None, **kwargs):
        if len(file_paths) == 0:
            raise Exception('No image file provided to BitmapWithPaletteSerializer')
        source = Image.open(file_paths[0])
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
        data['resource_id'] = '8Bit'
        data['width'] = im.width
        data['height'] = im.height
        data['bitmap'] = list(im.getdata())
        return data
