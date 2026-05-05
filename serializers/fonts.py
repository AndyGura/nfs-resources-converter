from typing import List

from library.read_blocks import DataBlock
from library.utils import path_join
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

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs) -> List[str]:
        super().serialize(data, path, id=id, block=None)
        image_serializer = ImageSerializer()
        (bblock, bdata) = block.get_child_block_with_data(data, 'bitmap/data')
        output = image_serializer.serialize(bdata, path_join(path, 'bitmap'), block=bblock)
        fnt_path = path_join(path, 'font.fnt')
        with open(fnt_path, 'w') as file:
            file.write(f'info face="{id.split("/")[-1]}" size={data["font_size"]}\n')
            file.write(f'common lineHeight={data["line_height"]}\n')
            file.write(f'page id=0 file="bitmap.png"\n')
            file.write(f'chars count={data["num_glyphs"]}\n')
            for symbol in data['definitions']:
                file.write(f'char id={symbol["code"]}    x={symbol["x"]}     y={symbol["y"]}     '
                           f'width={symbol["width"]}    height={symbol["height"]}   '
                           f'xoffset={symbol["x_offset"]}     yoffset={symbol["y_offset"]}     '
                           f'xadvance={symbol["advance"]}    page=0  chnl=0\n')
        output.append(fnt_path)
        return output

    def deserialize(self, file_paths: List[str], id=None, block: DataBlock = None, **kwargs):
        import re
        data = block.new_data()
        image_serializer = ImageSerializer()
        # FIXME only Bitmap4Bit is supported here
        data['bitmap']['data'] = image_serializer.deserialize(path_join(path, 'bitmap'),
                                                              block=block.get_child_block_with_data(data, 'bitmap')[0].possible_blocks[0])
        with open(path_join(path, 'font.fnt')) as f:
            lines = [l.rstrip() for l in f]
            info_part = '\n'.join([l for l in lines if not l.startswith('char ')])
            data['num_glyphs'] = int(re.search(r"\scount=(\d+)", info_part).groups()[0])
            glyph_def_lines = [l for l in lines if l.startswith('char ')]
            assert len(glyph_def_lines) == data['num_glyphs']
            data['definitions'] = []
            for i, glyph_def in enumerate(glyph_def_lines):
                m = re.search(
                    r"char\sid=(\d+).*\sx=(\d+).*\sy=(\d+).*\swidth=(\d+).*\sheight=(\d+).*\sxoffset=(-?\d+).*\syoffset=(-?\d+).*\sxadvance=(-?\d+).*",
                    glyph_def)
                if not m:
                    continue
                values = [int(x) for x in m.groups()]
                glyph_data = {
                    'code': values[0],
                    'x': values[1],
                    'y': values[2],
                    'width': values[3],
                    'height': values[4],
                    'x_offset': values[5],
                    'y_offset': values[6],
                    'advance': values[7],
                }
                glyph_data['x_advance'] = 0
                glyph_data['num_kern'] = 0
                glyph_data['kern_index'] = 0
                data['definitions'].append(glyph_data)
        return data
