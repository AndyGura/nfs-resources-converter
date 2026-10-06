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
            'reversible_settings_patch': {},
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

    def _get_palette_colors(self, data: dict, block, id) -> List[int]:
        palette_colors = []
        if data['resource_id'].startswith('8Bit'):
            (_, palette_data) = determine_palette_for_8_bit_bitmap(block, data, id)
            if palette_data is None:
                palette_colors = [0xFFFFFF00 | i for i in range(256)]
            else:
                palette_colors = [c for c in palette_data['colors']['data']]
                if palette_data['last_color_transparent']:
                    palette_colors[255] = 0
        return palette_colors

    def to_image(self, data: dict, block=None, id=None, palette_colors=None) -> Image.Image:
        if palette_colors is None:
            palette_colors = self._get_palette_colors(data, block, id)
        bitmap = self._transform_to_rgba(data['resource_id'], data['bitmap'], palette_colors)
        return Image.frombytes(
            'RGBA', (data['width'], data['height']), bytes().join([c.to_bytes(4, 'big') for c in bitmap])
        )

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs) -> List[str]:
        super().serialize(data, path, id=id, block=block)

        palette_colors = self._get_palette_colors(data, block, id)

        file_path = escape_chars(path)
        if not file_path.endswith('.png'):
            file_path += '.png'
        saved_files = [file_path]
        self.to_image(data, palette_colors=palette_colors).save(file_path)
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
                    bytes().join([c.to_bytes(4, 'big') for c in mipmaps_data[offset : offset + width * height]]),
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
                    pal_serializer.serialize(data[field_name], pal_path, block=EacPalette(), id=id + field_name)
                    saved_files.append(pal_path)
        if self.settings.images__save_texts and data.get('text'):
            text_serializer = ShpiTextSerializer()
            text_path = f'{file_path[:-4]}_extra'
            text_serializer.serialize(data['text'], text_path, block=ShpiText(), id=id + '/text')
            saved_files.append(text_path)
        return saved_files

    def deserialize(self, file_paths: List[str], id=None, block=None, **kwargs):
        if len(file_paths) == 0:
            raise Exception('No image file provided to ImageSerializer')
        if len(file_paths) != 1:
            raise Exception('ImageSerializer can only deserialize one file at once')
        image = Image.open(file_paths[0])
        image_rgba = image.convert('RGBA')
        data = block.new_data()
        data['resource_id'] = '32Bit color format bitmap'
        data['width'] = image.width
        data['height'] = image.height
        bitmap = [(r << 24) | (g << 16) | (b << 8) | a for (r, g, b, a) in image_rgba.get_flattened_data()]
        data['bitmap'] = bitmap
        return data


class TargaImageSerializer(BaseFileSerializer):
    def ui_serialization(self):
        return {
            'file_type': 'png',
            'is_directory': False,
            'output_file_name_suffix': '.png',
            'reversible': True,
            'reversible_settings_patch': {},
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
            'reversible_settings_patch': {},
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


# Direct3D formats of NFS Underground textures
_NFSU_D3D_A8R8G8B8 = 0x15
_NFSU_D3D_P8 = 0x29
_NFSU_DXT_FOURCC = {int.from_bytes(x.encode(), 'little'): x for x in ['DXT1', 'DXT3', 'DXT5']}


def _sub_chunk(container: dict, chunk_id: int):
    for chunk in container['sub_chunks']:
        if chunk['data'].get('chunk_id') == chunk_id:
            return chunk['data']
    return None


def nfsu_texture_pack_textures(tpk_data: dict) -> List[tuple]:
    """Textures of NFS Underground texture pack (TPK chunk data): list of (texture info, Direct3D format, data
    chunk bytes). Texture info offsets point into the data chunk bytes"""
    info_container = _sub_chunk(tpk_data, 0xB3310000)
    data_container = _sub_chunk(tpk_data, 0xB3320000)
    if info_container is None or data_container is None:
        return []
    infos = _sub_chunk(info_container, 0x33310004)
    formats = _sub_chunk(info_container, 0x33310005)
    data_chunk = _sub_chunk(data_container, 0x33320002)
    if infos is None or data_chunk is None:
        return []
    format_values = [f['format'] for f in formats['formats']] if formats else []
    return [
        (info, format_values[i] if i < len(format_values) else None, data_chunk['data'])
        for i, info in enumerate(infos['textures'])
    ]


def nfsu_texture_to_image(info: dict, d3d_format: int, data: bytes) -> Image.Image:
    """Full-size image of NFS Underground texture"""
    import numpy as np
    from library.utils.dxt import decode_dxt, dxt_byte_len

    width, height = info['width'], info['height']
    offset = info['image_placement']
    if d3d_format in _NFSU_DXT_FOURCC:
        dxt_format = _NFSU_DXT_FOURCC[d3d_format]
        pixels = decode_dxt(dxt_format, width, height, data[offset : offset + dxt_byte_len(dxt_format, width, height)])
        return Image.frombytes('RGBA', (width, height), np.array(pixels, dtype='>u4').tobytes())
    if d3d_format == _NFSU_D3D_A8R8G8B8:
        return Image.frombytes('RGBA', (width, height), data[offset : offset + width * height * 4], 'raw', 'BGRA')
    if d3d_format == _NFSU_D3D_P8:
        indices = np.frombuffer(data[offset : offset + width * height], dtype=np.uint8)
        palette_offset = info['palette_placement']
        palette = np.frombuffer(data[palette_offset : palette_offset + 1024], dtype=np.uint8)
        palette = np.pad(palette, (0, 1024 - len(palette))).reshape(256, 4)[:, [2, 1, 0, 3]]
        return Image.frombytes('RGBA', (width, height), palette[indices].tobytes())
    raise NotImplementedError(f'Unsupported NFSU texture format {d3d_format}')


class NfsuTexturePackSerializer(BaseFileSerializer):
    """Texture pack: every texture as "<name>.png" """

    def __init__(self):
        super().__init__(is_dir=True)

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs) -> List[str]:
        import os
        import re
        import traceback

        super().serialize(data, path, id=id, block=block)
        os.makedirs(path, exist_ok=True)
        files = []
        for info, d3d_format, image_data in nfsu_texture_pack_textures(data):
            name = re.sub(r'[^0-9A-Za-z_-]', '_', info['name']) or f'{info["name_hash"]:08x}'
            try:
                image = nfsu_texture_to_image(info, d3d_format, image_data)
            except Exception:
                traceback.print_exc()
                continue
            file_path = os.path.join(path, f'{name}.png')
            image.save(file_path)
            files.append(file_path)
        return files
