import os
import shlex
from copy import deepcopy
from typing import List

from library.exceptions import SerializationException
from library.read_blocks import DataBlock
from library.utils import path_join
from library.utils.id import join_id
from serializers import BaseFileSerializer, ImageSerializer


class FfnFontSerializer(BaseFileSerializer):
    def __init__(self):
        super().__init__(is_dir=True)

    def ui_serialization(self):
        return {
            'file_type': 'fnt + png',
            'is_directory': False,
            'output_file_name_suffix': None,
            'reversible': True,
            'reversible_settings_patch': {},
        }

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs) -> List[str]:
        super().serialize(data, path, id=id, block=None)
        image_serializer = ImageSerializer()
        (bblock, bdata) = block.get_child_block_with_data(data, 'bitmap')
        output = image_serializer.serialize(bdata, path_join(path, 'bitmap'), block=bblock, id=join_id(id, 'bitmap'))
        fnt_path = path_join(path, 'font.fnt')

        with open(fnt_path, 'w') as file:

            def write_fnt_line(prefix: str, data: dict) -> str:
                parts = [prefix] if prefix else []
                for key, value in data.items():
                    if isinstance(value, str):
                        value = f'"{value}"'
                    elif isinstance(value, bytes):
                        value = f'"{value.hex()}"'
                    parts.append(f'{key}={value}')
                file.write(' '.join(parts) + '\n')

            write_fnt_line(
                'info',
                {
                    'face': id.split('/')[-1],
                    'size': data['ascent'] + data['descent'],
                    'smooth': 1 if data['flags']['antialiased'] else 0,
                    'outline': 1 if data['flags']['outline'] else 0,
                },
            )
            write_fnt_line('common', {'lineHeight': data['ascent'] + data['descent'], 'base': data['ascent']})
            write_fnt_line(
                '#custom',
                {
                    'resource_id': data['resource_id'],
                    'version': data['version'],
                    'dropshadow': 1 if data['flags']['dropshadow'] else 0,
                    'vram': 1 if data['flags']['vram'] else 0,
                    'drawpad': data['flags']['drawpad'],
                    'baseline': data['flags']['baseline'],
                    'orientation': data['flags']['orientation'],
                    'direction': data['flags']['direction'],
                    'layoutpad': data['flags']['layoutpad'],
                    'encoding': data['flags']['encoding'],
                    'format': data['flags']['format'],
                    'pad': data['flags']['pad'],
                    'center_x': data['center']['x'],
                    'center_y': data['center']['y'],
                    'padding_0': data['padding_0'],
                    'padding_1': data.get('padding_1'),
                    'padding_2': data['padding_2'],
                    'remaining_bytes': data['remaining_bytes'],
                },
            )
            write_fnt_line('page', {'id': 0, 'file': 'bitmap.png'})
            write_fnt_line('chars', {'count': data['num_glyphs']})
            # 16-byte glyphs keep the advance in x_advance (advance is 0 in the game files). In 12-byte ones the
            # absent x_advance reads as 0, never None
            is_16_bytes = data['version'] >= 321 and data['flags']['format'] == '16-bytes'
            for symbol in data['definitions']:
                char_data = {
                    'id': symbol['code'],
                    'x': symbol['x'],
                    'y': symbol['y'],
                    'width': symbol['width'],
                    'height': symbol['height'],
                    'xoffset': symbol['x_offset'],
                    'yoffset': symbol['y_offset'],
                    'xadvance': symbol['x_advance'] if is_16_bytes else symbol['advance'],
                    'page': 0,
                    'chnl': 0,
                }
                if is_16_bytes:
                    char_data['advance'] = symbol['advance']
                if symbol.get('num_kern') is not None:
                    char_data['num_kern'] = symbol['num_kern']
                if symbol.get('kern_index') is not None:
                    char_data['kern_index'] = symbol['kern_index']
                if symbol.get('x_advance') is not None:
                    char_data['x_advance'] = symbol['x_advance']
                if symbol.get('pad') is not None:
                    char_data['pad'] = symbol['pad']
                write_fnt_line('char', char_data)
            if data.get('kernings'):
                write_fnt_line('kernings', {'count': len(data['kernings'])})
                for kerning in data['kernings']:
                    write_fnt_line(
                        'kerning', {'first': kerning['left'], 'second': kerning['right'], 'amount': kerning['kerning']}
                    )
        output.append(fnt_path)
        return output

    def deserialize(self, file_paths: List[str], id=None, block: DataBlock = None, **kwargs):
        (fnt_file_path, lines, png_path) = self._import_files(file_paths)
        current = self._current_font(id)
        data = block.new_data()
        if current is not None:
            # a .fnt without the #custom line (BMFont, Hiero) keeps the header and layout of the font it replaces
            for name in [
                'resource_id',
                'version',
                'flags',
                'center',
                'padding_0',
                'padding_2',
                'bdata_ptr',
                'remaining_bytes',
            ]:
                data[name] = deepcopy(current[name])
        image_serializer = ImageSerializer()
        data['bitmap'] = image_serializer.deserialize([png_path], block=block.get_child_block('bitmap'))
        if current is not None:
            self._keep_bitmap_format(data['bitmap'], current['bitmap'])

        def parse_fnt_char_line(line: str) -> dict:
            parts = shlex.split(line.strip())
            result = {}
            for part in parts:
                if '=' in part:
                    key, value = part.split('=', 1)
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    else:
                        try:
                            value = int(value)
                        except ValueError:
                            pass
                    result[key] = value
            return result

        info_part = parse_fnt_char_line(next(l for l in lines if l.startswith('info ')))
        if 'smooth' in info_part:
            data['flags']['antialiased'] = info_part['smooth'] == 1
        if 'outline' in info_part:
            data['flags']['outline'] = info_part['outline'] != 0

        common_part = parse_fnt_char_line(next(l for l in lines if l.startswith('common ')))
        if 'base' in common_part:
            data['ascent'] = common_part['base']
        if 'lineHeight' in common_part:
            data['descent'] = common_part['lineHeight'] - data['ascent']

        try:
            custom_part = parse_fnt_char_line(next(l for l in lines if l.startswith('#custom ')))
            if 'resource_id' in custom_part:
                data['resource_id'] = custom_part['resource_id']
            if 'version' in custom_part:
                data['version'] = custom_part['version']
            if 'dropshadow' in custom_part:
                # older exports wrote True / False
                data['flags']['dropshadow'] = custom_part['dropshadow'] in (1, 'True')
            if 'vram' in custom_part:
                data['flags']['vram'] = custom_part['vram'] == 1
            if 'drawpad' in custom_part:
                data['flags']['drawpad'] = custom_part['drawpad']
            if 'baseline' in custom_part:
                data['flags']['baseline'] = custom_part['baseline']
            if 'orientation' in custom_part:
                data['flags']['orientation'] = custom_part['orientation']
            if 'direction' in custom_part:
                data['flags']['direction'] = custom_part['direction']
            if 'layoutpad' in custom_part:
                data['flags']['layoutpad'] = custom_part['layoutpad']
            if 'encoding' in custom_part:
                data['flags']['encoding'] = custom_part['encoding']
            if 'format' in custom_part:
                data['flags']['format'] = custom_part['format']
            if 'pad' in custom_part:
                data['flags']['pad'] = custom_part['pad']
            if 'center_x' in custom_part:
                data['center']['x'] = custom_part['center_x']
            if 'center_y' in custom_part:
                data['center']['y'] = custom_part['center_y']
            if 'padding_0' in custom_part:
                data['padding_0'] = bytes.fromhex(str(custom_part['padding_0']))
            if 'padding_1' in custom_part and custom_part['padding_1'] is not None:
                data['padding_1'] = bytes.fromhex(str(custom_part['padding_1'])) if custom_part['padding_1'] else b''
            if 'padding_2' in custom_part:
                data['padding_2'] = bytes.fromhex(str(custom_part['padding_2']))
            if 'remaining_bytes' in custom_part:
                data['remaining_bytes'] = bytes.fromhex(str(custom_part['remaining_bytes']))
        except StopIteration:
            pass

        glyph_def_lines = [parse_fnt_char_line(l) for l in lines if l.startswith('char ')]
        data['definitions'] = []
        is_16_bytes = data['version'] >= 321 and data['flags']['format'] == '16-bytes'
        for values in glyph_def_lines:
            glyph_data = {
                'code': values['id'],
                'x': values['x'],
                'y': values['y'],
                'width': values['width'],
                'height': values['height'],
                'x_offset': values['xoffset'],
                'y_offset': values['yoffset'],
                'advance': values['xadvance'],
            }
            if 'advance' in values:
                glyph_data['advance'] = values['advance']
            elif 'x_advance' not in values and is_16_bytes:
                # BMFont into a 16-byte glyph font: the advance goes to x_advance, as in the game files
                glyph_data['advance'] = 0
            glyph_data['num_kern'] = values.get('num_kern', 0)
            glyph_data['x_advance'] = values.get('x_advance', values['xadvance'])
            glyph_data['kern_index'] = values.get('kern_index', 0)
            glyph_data['pad'] = values.get('pad', 0)
            data['definitions'].append(glyph_data)

        kerning_lines = [parse_fnt_char_line(l) for l in lines if l.startswith('kerning ')]
        too_big = [x for x in kerning_lines if x['second'] > 255]
        if too_big:
            raise SerializationException(
                f'FFN kerning pairs keep the right glyph code in 1 byte (0..255), but {len(too_big)} kerning '
                f'lines of the .fnt have a bigger "second", e.g. first={too_big[0]["first"]} '
                f'second={too_big[0]["second"]}. Remove them from the .fnt and import again'
            )
        data['kernings'] = []
        for values in kerning_lines:
            data['kernings'].append(
                {
                    'left': values['first'],
                    'right': values['second'],
                    'kerning': values['amount'],
                }
            )
        return data

    @staticmethod
    def _import_files(file_paths: List[str]):
        # the .fnt, its lines and the PNG atlas: a picked PNG, else the one its page line names, next to the .fnt.
        # A picked folder is searched for the .fnt
        file_paths = [
            path_join(x, name) if os.path.isdir(x) else x
            for x in file_paths
            for name in (sorted(os.listdir(x)) if os.path.isdir(x) else [None])
        ]
        fnt_paths = [x for x in file_paths if x.lower().endswith('.fnt')]
        if len(fnt_paths) != 1:
            raise SerializationException(
                'Pick the .fnt file of the font' if not fnt_paths else 'Pick only one .fnt file'
            )
        with open(fnt_paths[0]) as f:
            lines = [l.rstrip() for l in f]
        png_paths = [x for x in file_paths if x.lower().endswith('.png')]
        if png_paths:
            return fnt_paths[0], lines, png_paths[0]
        pages = []
        for line in lines:
            if line.startswith('page '):
                file_name = next((x[len('file=') :] for x in shlex.split(line) if x.startswith('file=')), None)
                pages.append(file_name)
        if len(pages) > 1:
            raise SerializationException(
                f'The .fnt uses {len(pages)} atlas pages, an FFN font has one. Export it with a single page'
            )
        png_path = path_join(os.path.dirname(fnt_paths[0]), pages[0]) if pages and pages[0] else None
        if png_path is None or not os.path.isfile(png_path):
            raise SerializationException(
                f'The .fnt names its atlas "{pages[0] if pages else ""}", which is not next to it. '
                f'Pick the PNG together with the .fnt'
            )
        return fnt_paths[0], lines, png_path

    @staticmethod
    def _current_font(id: str):
        # the font loaded under `id`, which the import replaces
        from library import require_resource

        try:
            (_, _, current), _ = require_resource(id)
            return current if isinstance(current, dict) and 'bitmap' in current else None
        except Exception:
            return None

    @staticmethod
    def _keep_bitmap_format(bitmap: dict, current_bitmap: dict):
        # The imported bitmap takes the format of the atlas it replaces, with its embedded palette (NFS6), instead of
        # 32-bit colors: 4Bit from the alpha channel (the exported glyph mask), 8Bit by the colors of the current
        # palette (NFS6 outline fonts mix black and white entries)
        from resources.eac.bitmaps import EacImage

        current_format = current_bitmap['resource_id']
        if current_format.startswith('4Bit'):
            EacImage().action_convert_to_4bit(bitmap, current_format, 'alpha')
        elif current_format == '8Bit':
            palette = current_bitmap.get('embedded_palette')
            if palette and palette['resource_id'] == '32Bit color format palette':
                bitmap['bitmap'] = ImageSerializer.to_palette_indexes(bitmap['bitmap'], palette['colors']['data'])
                bitmap['resource_id'] = '8Bit'
            else:
                EacImage().action_convert_to_8bit(bitmap, 'alpha')
        else:
            return
        for name in ['pad', 'embedded_palette', 'embedded_palette_pad']:
            bitmap[name] = deepcopy(current_bitmap.get(name))
