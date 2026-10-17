from copy import deepcopy
from io import BytesIO
from typing import List, Optional, Sequence

import numpy as np
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
        if not data['resource_id'].startswith('8Bit'):
            return []
        palette_colors = self._found_palette_colors(data, block, id)
        if palette_colors is None:
            return [0xFFFFFF00 | i for i in range(256)]
        return palette_colors

    @staticmethod
    def _found_palette_colors(data: dict, block, id) -> Optional[List[int]]:
        # the colors of the palette of an 8Bit bitmap as it is exported, None when it has none
        (_, palette_data) = determine_palette_for_8_bit_bitmap(block, data, id)
        if palette_data is None:
            return None
        palette_colors = [c for c in palette_data['colors']['data']]
        if id and '.CFM__' in id.upper():
            from serializers.misc.tnfs_car_colors import car_texture_palette

            # TNFS car textures: unique colors of the indices car_colors.json lists
            palette_colors = car_texture_palette(palette_colors)
        if palette_data['last_color_transparent']:
            palette_colors[255] = 0
        return palette_colors

    def to_image(self, data: dict, block=None, id=None, palette_colors=None) -> Image.Image:
        """The image as it is exported, always RGBA"""
        if palette_colors is None:
            palette_colors = self._get_palette_colors(data, block, id)
        bitmap = self._transform_to_rgba(data['resource_id'], data['bitmap'], palette_colors)
        return Image.frombytes(
            'RGBA', (data['width'], data['height']), bytes().join([c.to_bytes(4, 'big') for c in bitmap])
        )

    def to_png_image(self, data: dict, block=None, id=None, palette_colors=None) -> Image.Image:
        """The image as it is saved to PNG: an 8Bit image is indexed (`indexed_image`), the others are `to_image`"""
        if palette_colors is None:
            palette_colors = self._get_palette_colors(data, block, id)
        if data['resource_id'].startswith('8Bit'):
            image = self.indexed_image(data['bitmap'], data['width'], data['height'], palette_colors)
            if image is not None:
                return image
        return self.to_image(data, palette_colors=palette_colors)

    @staticmethod
    def indexed_image(
        indexes: Sequence[int], width: int, height: int, palette_colors: List[int]
    ) -> Optional[Image.Image]:
        """8Bit pixels as an indexed (P) image which decodes to the RGBA of `to_image`, bytes under alpha 0 included:
        the pixels keep their indexes (duplicate palette colors are not merged), entry i is `palette_colors[i]`
        (transparent black past its end), RGB in PLTE, alpha in tRNS. The palette ends at the last index used, tRNS
        at the last entry not opaque (none when all are). None when an index is not 0..255"""
        try:
            pixels = bytes(indexes[: width * height])
        except ValueError, TypeError:
            return None
        if len(pixels) < width * height:
            return None
        count = max(pixels, default=0) + 1
        colors = list(palette_colors[:count]) + [0] * max(0, count - len(palette_colors))
        image = Image.frombytes('P', (width, height), pixels)
        image.putpalette(b''.join((c >> 8).to_bytes(3, 'big') for c in colors), 'RGB')
        alpha = bytes(c & 0xFF for c in colors).rstrip(b'\xff')
        if alpha:
            image.info['transparency'] = alpha
        return image

    @staticmethod
    def save_png(image: Image.Image, file_path: str):
        """Saves an image made by `to_png_image`. Indexed images get the best zlib compression, they are small"""
        image.save(file_path, **({'compress_level': 9} if image.mode == 'P' else {}))

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs) -> List[str]:
        super().serialize(data, path, id=id, block=block)

        palette_colors = self._get_palette_colors(data, block, id)

        file_path = escape_chars(path)
        if not file_path.endswith('.png'):
            file_path += '.png'
        saved_files = [file_path]
        self.save_png(self.to_png_image(data, palette_colors=palette_colors), file_path)
        if data.get('mipmaps') and self.settings.images__save_mipmaps:
            from resources.eac.bitmaps import mipmap_level_dims

            is_8bit = data['resource_id'].startswith('8Bit')
            mipmaps_data = (
                data['mipmaps']
                if is_8bit
                else self._transform_to_rgba(data['resource_id'], data['mipmaps'], palette_colors)
            )
            offset = 0
            # every level down to 1x1, also for non-square images (64x128: 7 levels, the last 1x1)
            for mipmap_index, (width, height) in enumerate(mipmap_level_dims(data['width'], data['height'])):
                mipmap_path = f'{file_path[:-4]}_mm_{mipmap_index}.png'
                level = mipmaps_data[offset : offset + width * height]
                image = self.indexed_image(level, width, height, palette_colors) if is_8bit else None
                if image is None:
                    rgba = self._transform_to_rgba(data['resource_id'], level, palette_colors) if is_8bit else level
                    image = Image.frombytes('RGBA', (width, height), bytes().join([c.to_bytes(4, 'big') for c in rgba]))
                self.save_png(image, mipmap_path)
                saved_files.append(mipmap_path)
                offset += width * height
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
        """The image loaded under `id` with the pixels of the image file: format, position, hot spots, text and the
        other fields are kept, mipmaps are made again. Without such an image, a new 32-bit one"""
        if len(file_paths) == 0:
            raise Exception('No image file provided to ImageSerializer')
        if len(file_paths) != 1:
            raise Exception('ImageSerializer can only deserialize one file at once')
        current = self._current_image(id)
        if current is None:
            return self.new_image_data(file_paths[0], block)
        return self._with_pixels_of(current, file_paths[0], block, id)

    @staticmethod
    def new_image_data(file_path: str, block) -> dict:
        """A new 32-bit image with the pixels of the image file"""
        image = Image.open(file_path)
        image_rgba = image.convert('RGBA')
        data = block.new_data()
        data['resource_id'] = '32Bit color format bitmap'
        data['width'] = image.width
        data['height'] = image.height
        bitmap = [(r << 24) | (g << 16) | (b << 8) | a for (r, g, b, a) in image_rgba.get_flattened_data()]
        data['bitmap'] = bitmap
        return data

    @staticmethod
    def _current_image(id) -> Optional[dict]:
        # the image loaded under `id`, which the import replaces
        if not id:
            return None
        from library import require_resource

        try:
            (_, _, current), _ = require_resource(id)
        except Exception:
            return None
        return current if isinstance(current, dict) and 'bitmap' in current and 'resource_id' in current else None

    def _with_pixels_of(self, current: dict, file_path: str, block, id) -> dict:
        from library.utils.number_utils import is_power_of_two

        new_image = self.new_image_data(file_path, block)
        width, height, pixels = new_image['width'], new_image['height'], new_image['bitmap']
        color_format = current['resource_id']
        # the palette the image is exported with (without one in the file, the index in the alpha channel), looked
        # up before the change: the palette of an image is found by comparing the image data
        palette_colors = self._get_palette_colors(current, block, id)
        data = {k: (v if k in ('bitmap', 'mipmaps') else deepcopy(v)) for k, v in current.items()}
        data['width'], data['height'] = width, height
        if color_format == '8Bit':
            exact_only = []
            if id and '.CFM__' in id.upper():
                from serializers.misc.tnfs_car_colors import LIGHT_BAR_INDICES, TAIL_LIGHT_INDEX

                # the game recolors these: only pixels of exactly their color take them
                exact_only = LIGHT_BAR_INDICES + [TAIL_LIGHT_INDEX]
            data['bitmap'] = self.to_palette_indexes(pixels, palette_colors, exact_only)
            if (width, height) == (current['width'], current['height']):
                data['bitmap'] = self._keep_unchanged_indexes(data['bitmap'], current['bitmap'], pixels, palette_colors)
        elif color_format.startswith('4Bit'):
            # the exported 4Bit image is white with the 4-bit value in the alpha channel
            data['bitmap'] = block._convert_pixels_to_4bit(
                pixels, '32Bit color format bitmap', 'alpha', [(width, height)]
            )
        elif color_format != '32Bit color format bitmap':
            # the colors the format can hold, as the color model conversion does
            data['bitmap'] = block._native_to_internal(
                color_format, width, height, block._internal_to_native(color_format, width, height, pixels)
            )
        else:
            data['bitmap'] = pixels
        if current.get('mipmaps') is not None and data['bitmap'] != current['bitmap']:
            data['mipmaps'] = None
            if is_power_of_two(width) and is_power_of_two(height) and (width > 1 or height > 1):
                block.action_generate_mipmaps(data)
        return data

    @staticmethod
    def _keep_unchanged_indexes(indexes: List[int], current_indexes: List[int], pixels: List[int], palette: List[int]):
        # a pixel which still has the color of its index keeps that index: a palette can have one color several times
        colors = np.asarray(palette + [0], dtype=np.uint32)
        current = np.asarray(current_indexes, dtype=np.int64)
        current_colors = colors[np.where((current >= 0) & (current < len(palette)), current, len(palette))]
        unchanged = current_colors == np.asarray(pixels, dtype=np.uint32)
        return np.where(unchanged, current, np.asarray(indexes, dtype=np.int64)).tolist()

    @staticmethod
    def to_palette_indexes(pixels: List[int], palette: List[int], exact_only: Sequence[int] = ()) -> List[int]:
        """RGBA pixels -> indexes of the same palette color (the first one), else of the nearest one (a transparent
        pixel takes a transparent entry when there is one). The `exact_only` indexes are taken by their exact color
        only"""
        if len(pixels) == 0:
            return []
        first_index = {}
        for i, color in enumerate(palette):
            first_index.setdefault(color, i)
        candidates = [i for i in range(len(palette)) if i not in exact_only] or list(range(len(palette)))
        transparent = [i for i in candidates if palette[i] & 0xFF == 0]

        def channels(colors):
            colors = np.asarray(colors, dtype=np.uint32)
            return np.stack([(colors >> shift) & 0xFF for shift in (24, 16, 8, 0)], axis=-1).astype(np.int32)

        unique_pixels, inverse = np.unique(np.asarray(pixels, dtype=np.uint32), return_inverse=True)
        unique_indexes = np.zeros(len(unique_pixels), dtype=np.int64)
        to_search = []
        for n, pixel in enumerate(unique_pixels.tolist()):
            if pixel in first_index:
                unique_indexes[n] = first_index[pixel]
            elif pixel & 0xFF == 0 and transparent:
                unique_indexes[n] = transparent[0]
            else:
                to_search.append(n)
        if to_search:
            candidate_channels = channels([palette[i] for i in candidates])
            searched = channels(unique_pixels[to_search])
            nearest = []
            for start in range(0, len(searched), 4096):
                chunk = searched[start : start + 4096]
                distances = ((chunk[:, None, :] - candidate_channels[None, :, :]) ** 2).sum(axis=-1)
                nearest.extend(np.asarray(candidates)[distances.argmin(axis=1)].tolist())
            unique_indexes[to_search] = nearest
        return unique_indexes[inverse.reshape(-1)].tolist()


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


def _nfsu_compressed_textures(compressed: dict, data: bytes) -> List[tuple]:
    from io import BytesIO
    from resources.blackbox.bitmaps.nfsu import NfsuTextureFormat, NfsuTextureInfo
    from resources.eac.compressions.huff import HuffCompression
    from resources.eac.compressions.jdlz import JdlzCompression

    entries = compressed['textures']
    if not entries:
        return []
    # offsets are absolute in the file; the first texture starts the data chunk payload
    base = min(e['offset'] for e in entries)
    res = []
    for e in entries:
        blob = data[e['offset'] - base : e['offset'] - base + e['compressed_size']]
        if blob[:4] == b'JDLZ':
            raw = JdlzCompression().uncompress(BytesIO(blob), len(blob))
        elif blob[:4] == b'HUFF':
            raw = HuffCompression().uncompress(BytesIO(blob), len(blob))
        else:
            continue
        info = NfsuTextureInfo().unpack_from_bytes(raw[-156:-32])
        d3d_format = NfsuTextureFormat().unpack_from_bytes(raw[-32:])['format']
        # image data starts the uncompressed texture, palette follows it
        info = {
            **info,
            'image_placement': 0,
            'palette_placement': info['palette_placement'] - info['image_placement'],
        }
        res.append((info, d3d_format, raw[:-156]))
    return res


def nfsu_texture_pack_textures(tpk_data: dict) -> List[tuple]:
    """Textures of NFS Underground texture pack (TPK chunk data): list of (texture info, Direct3D format, data
    bytes). Texture info offsets point into the data bytes: the data chunk of the pack, or the uncompressed texture
    of NFSU2 compressed pack"""
    info_container = _sub_chunk(tpk_data, 0xB3310000)
    data_container = _sub_chunk(tpk_data, 0xB3320000)
    if info_container is None or data_container is None:
        return []
    infos = _sub_chunk(info_container, 0x33310004)
    formats = _sub_chunk(info_container, 0x33310005)
    compressed = _sub_chunk(info_container, 0x33310003)
    data_chunk = _sub_chunk(data_container, 0x33320002)
    if data_chunk is None:
        return []
    if infos is None:
        return _nfsu_compressed_textures(compressed, data_chunk['data']) if compressed else []
    format_values = [f['format'] for f in formats['formats']] if formats else []
    return [
        (info, format_values[i] if i < len(format_values) else None, data_chunk['data'])
        for i, info in enumerate(infos['textures'])
    ]


def nfsu_texture_to_image(info: dict, d3d_format: int, data: bytes, indexed: bool = False) -> Image.Image:
    """Full-size image of NFS Underground texture, RGBA. With `indexed`, a palettized (P8) texture is an indexed image
    (`ImageSerializer.indexed_image`) of the same RGBA, to save it to PNG"""
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
        if indexed and len(indices) == width * height:
            colors = np.frombuffer(np.ascontiguousarray(palette).tobytes(), dtype='>u4').tolist()
            return ImageSerializer.indexed_image(indices.tolist(), width, height, colors)
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
                image = nfsu_texture_to_image(info, d3d_format, image_data, indexed=True)
            except Exception:
                traceback.print_exc()
                continue
            file_path = os.path.join(path, f'{name}.png')
            ImageSerializer.save_png(image, file_path)
            files.append(file_path)
        return files
