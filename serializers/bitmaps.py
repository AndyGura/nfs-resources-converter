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
        super().serialize(data, path, id=id, block=block)
        if data['resource_id'].startswith('8Bit'):
            (palette_block, palette_data) = determine_palette_for_8_bit_bitmap(block, data, id)
            bitmap = []
            if palette_block is None:
                palette_colors = [0xffffff00 | i for i in range(256)]
            else:
                palette_colors = [c for c in palette_data['colors']['data']]
                if palette_data['last_color_transparent']:
                    palette_colors[255] = 0
            for index in data['bitmap']:
                try:
                    bitmap.append(palette_colors[index])
                except IndexError:
                    bitmap.append(0)
        elif data['resource_id'].startswith('4Bit'):
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
