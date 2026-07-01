import shlex
from typing import List

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
            'reversible_settings_patch': {}
        }

    # TODO not used fields in serialize/deserialize:
    # [ ] definitions/kern_index - unknown
    # [ ] definitions/x_advance - not clear
    # [ ] kernings/left
    # [ ] kernings/unk
    # [ ] kernings/kerning
    # [ ] kernings/right

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
                    parts.append(f'{key}={value}')
                file.write(' '.join(parts) + '\n')

            write_fnt_line('info', {'face': id.split('/')[-1],
                                    'size': data['ascent'] + data['descent'],
                                    'smooth': 1 if data['flags']['antialiased'] else 0,
                                    'outline': 1 if data['flags']['outline'] else 0})
            write_fnt_line('common', {'lineHeight': data['ascent'] + data['descent'],
                                      'base': data['ascent']})
            write_fnt_line('#custom', {'resource_id': data['resource_id'],
                                       'version': data['version'],
                                       'dropshadow': data['flags']['dropshadow'],
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
                                       'center_y': data['center']['y'], })
            write_fnt_line('page', {'id': 0, 'file': 'bitmap.png'})
            write_fnt_line('chars', {'count': data['num_glyphs']})
            for symbol in data['definitions']:
                write_fnt_line('char',
                               {'id': symbol['code'],
                                'x': symbol['x'], 'y': symbol['y'], 'width': symbol['width'],
                                'height': symbol['height'], 'xoffset': symbol['x_offset'],
                                'yoffset': symbol['y_offset'], 'xadvance': symbol['advance'], 'page': 0,
                                'chnl': 0})
        output.append(fnt_path)
        return output

    def deserialize(self, file_paths: List[str], id=None, block: DataBlock = None, **kwargs):
        try:
            fnt_file_path = next(x for x in file_paths if x.endswith('.fnt'))
        except StopIteration:
            raise Exception('No .fnt file found in provided paths')

        data = block.new_data()
        image_serializer = ImageSerializer()
        data['bitmap'] = image_serializer.deserialize([x for x in file_paths if x.endswith('.png')],
                                                      block=block.get_child_block('bitmap'))
        with open(fnt_file_path) as f:
            lines = [l.rstrip() for l in f]

            def parse_fnt_char_line(line: str) -> dict:
                parts = shlex.split(line.strip())
                result = {}
                for part in parts:
                    if '=' in part:
                        key, value = part.split('=', 1)
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
                else:
                    data['version'] = 100  # TODO set bigger if other data requires newer features
                if 'dropshadow' in custom_part:
                    data['flags']['dropshadow'] = custom_part['dropshadow'] == 1
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
            except StopIteration:
                pass

            glyph_def_lines = [parse_fnt_char_line(l) for l in lines if l.startswith('char ')]
            data['definitions'] = []
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
                glyph_data['num_kern'] = 0
                glyph_data['x_advance'] = 0
                glyph_data['kern_index'] = 0
                data['definitions'].append(glyph_data)
        return data
