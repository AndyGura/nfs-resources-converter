from library.read_blocks import DataBlock
from library.utils import path_join
from serializers import BaseFileSerializer, BitmapSerializer


class FfnFontSerializer(BaseFileSerializer):

    def __init__(self):
        super().__init__(is_dir=True)

    def setup_for_reversible_serialization(self) -> bool:
        return True

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs):
        super().serialize(data, path, id=id, block=None)
        image_serializer = BitmapSerializer()
        image_serializer.serialize(data["bitmap"], path_join(path, 'bitmap'),
                                   block=block.get_child_block_with_data(data, 'bitmap')[0])
        with open(path_join(path, 'font.fnt'), 'w') as file:
            file.write(f'info face="{id.split("/")[-1]}" size={data["font_size"]}\n')
            file.write(f'common lineHeight={data["line_height"]}\n')
            file.write(f'page id=0 file="bitmap.png"\n')
            file.write(f'chars count={data["num_glyphs"]}\n')
            for symbol in data["definitions"]:
                file.write(f'char id={symbol["code"]}    x={symbol["x"]}     y={symbol["y"]}     '
                           f'width={symbol["width"]}    height={symbol["height"]}   '
                           f'xoffset={symbol["x_offset"]}     yoffset={symbol["y_offset"]}     '
                           f'xadvance={symbol["x_advance"]}    page=0  chnl=0\n')

    def deserialize(self, path: str, id=None, block: DataBlock = None, **kwargs):
        import re
        data = block.new_data()
        image_serializer = BitmapSerializer()
        data['bitmap'] = image_serializer.deserialize(path_join(path, 'bitmap'),
                                                      block=block.get_child_block_with_data(data, 'bitmap')[0])
        with open(path_join(path, 'font.fnt')) as f:
            lines = [l.rstrip() for l in f]
            info_part = '\n'.join([l for l in lines if not l.startswith('char ')])
            data['font_size'] = int(re.search(r"\ssize=(\d+)", info_part).groups()[0])
            data['line_height'] = int(re.search(r"\slineHeight=(\d+)", info_part).groups()[0])
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
                data['definitions'].append({
                    'code': values[0],
                    'x': values[1],
                    'y': values[2],
                    'width': values[3],
                    'height': values[4],
                    'x_offset': values[5],
                    'y_offset': values[6],
                    'x_advance': values[7],
                })
        return data
