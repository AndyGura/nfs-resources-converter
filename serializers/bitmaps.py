from io import BytesIO
from typing import List

from PIL import Image

from resources.eac.bitmaps import EacPalette, ShpiText
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

    def _transform_to_rgba(self, resource_id, data, palette_colors):
        if resource_id.startswith('8Bit'):
            bitmap = []
            for index in data:
                try:
                    bitmap.append(palette_colors[index])
                except IndexError:
                    bitmap.append(0)
            return bitmap
        elif resource_id.startswith('4Bit'):
            return [item for row in data for item in row]
        else:
            return data

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs) -> List[str]:
        super().serialize(data, path, id=id, block=block)

        palette_colors = []
        if data['resource_id'].startswith('8Bit'):
            (_, palette_data) = determine_palette_for_8_bit_bitmap(block, data, id)
            if palette_data is None:
                palette_colors = [0xffffff00 | i for i in range(256)]
            else:
                palette_colors = [c for c in palette_data['colors']['data']]
                if palette_data['last_color_transparent']:
                    palette_colors[255] = 0

        file_path = escape_chars(path)
        if not file_path.endswith('.png'):
            file_path += '.png'
        saved_files = [file_path]
        bitmap = self._transform_to_rgba(data['resource_id'], data['bitmap'], palette_colors)
        Image.frombytes('RGBA',
                        (data['width'], data['height']),
                        bytes().join([c.to_bytes(4, 'big') for c in bitmap])).save(file_path)
        if data.get('mipmaps') and self.settings.images__save_mipmaps:
            mipmaps_data = self._transform_to_rgba(data['resource_id'], data['mipmaps'], palette_colors)
            (width, height) = (data['width'], data['height'])
            offset = 0
            mipmap_index = 0
            while min(width, height) > 1:
                width //= 2
                height //= 2
                mipmap_path = f'{file_path[:-4]}_mm_{mipmap_index}.png'
                Image.frombytes(
                    'RGBA',
                    (width, height),
                    bytes().join([c.to_bytes(4, 'big') for c in mipmaps_data[offset:offset + width * height]])
                ).save(mipmap_path)
                saved_files.append(mipmap_path)
                offset += width * height
                mipmap_index += 1
        if self.settings.images__save_embedded_palette:
            pal_serializer = PaletteSerializer()
            for i in range(1, 5):
                if i > 1:
                    pal_path = f'{file_path[:-4]}_pal{i}.pal.txt'
                    field_name = f'embedded_palette_{i}'
                else:
                    pal_path = f'{file_path[:-4]}_pal.pal.txt'
                    field_name = f'embedded_palette'
                if data.get(field_name):
                    pal_serializer.serialize(data[field_name], pal_path,
                                             block=EacPalette(),
                                             id=id + field_name)
                    saved_files.append(pal_path)
        if self.settings.images__save_texts and data.get('text'):
            text_serializer = ShpiTextSerializer()
            text_path = f'{file_path[:-4]}_extra'
            text_serializer.serialize(data['text'], text_path,
                                     block=ShpiText(),
                                     id=id + '/text')
            saved_files.append(text_path)
        return saved_files

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
        bitmap = [
            (r << 24) | (g << 16) | (b << 8) | a
            for (r, g, b, a) in image_rgba.get_flattened_data()
        ]
        data['bitmap'] = bitmap
        return data


class TargaImageSerializer(BaseFileSerializer):

    def ui_serialization(self):
        return {
            'file_type': 'png',
            'is_directory': False,
            'output_file_name_suffix': '.png',
            'reversible': True,
            'reversible_settings_patch': {}
        }

    def serialize(self, data: bytes, path: str, id=None, block=None, **kwargs) -> List[str]:
        super().serialize(data, path, id=id, block=block)
        file_path = escape_chars(path)
        if not file_path.endswith('.png'):
            file_path += '.png'
        tga_image = Image.open(BytesIO(data))
        tga_image_rgba = tga_image.convert('RGBA')
        tga_image_rgba.save(file_path)
        return [file_path]

    def deserialize(self, file_paths: List[str], id=None, block=None, **kwargs):
        if len(file_paths) == 0:
            raise Exception('No image file provided to TargaImageSerializer')
        if len(file_paths) != 1:
            raise Exception('TargaImageSerializer can only deserialize one file at once')
        image = Image.open(file_paths[0])
        image_rgba = image.convert('RGBA')
        tga_buffer = BytesIO()
        image_rgba.save(tga_buffer, format='TGA')
        return tga_buffer.getvalue()


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


class ShpiTextSerializer(BaseFileSerializer):

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs) -> List[str]:
        super().serialize(data, path)
        with open(f'{path}.txt', 'w') as file:
            file.write(data['text'])
        return [f'{path}.txt']
