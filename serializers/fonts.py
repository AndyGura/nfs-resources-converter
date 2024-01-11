import os

from library.read_data import ReadData
from serializers import BaseFileSerializer, BitmapSerializer


class FfnFontSerializer(BaseFileSerializer):

    def setup_for_reversible_serialization(self) -> bool:
        self.patch_settings({
            'export_unknown_values': True,
        })
        return True

    def serialize(self, data: dict, path: str, name=None, block=None):
        super().serialize(data, path, is_dir=True, name=name, block=None)
        image_serializer = BitmapSerializer()
        image_serializer.serialize(data["bitmap"], os.path.join(path, 'bitmap'))
        with open(os.path.join(path, 'font.fnt'), 'w') as file:
            file.write(f'info face="{name.split("/")[-1]}" size={data["font_size"]}\n')
            file.write(f'common lineHeight={data["line_height"]}\n')
            file.write(f'page id=0 file="bitmap.png"\n')
            file.write(f'chars count={data["symbols_amount"]}\n')
            for symbol in data["definitions"]:
                file.write(f'char id={symbol["code"]}    x={symbol["glyph_x"]}     y={symbol["glyph_y"]}     '
                           f'width={symbol["glyph_width"]}    height={symbol["glyph_height"]}   '
                           f'xoffset={symbol["x_offset"]}     yoffset={symbol["y_offset"]}     '
                           f'xadvance={symbol["x_advance"]}    page=0  chnl=0\n')

    def deserialize(self, path: str, resource: ReadData, **kwargs) -> None:
        import re
        image_serializer = BitmapSerializer()
        image_serializer.deserialize(os.path.join(path, 'bitmap'), resource['bitmap'])
        with open(os.path.join(path, 'font.fnt')) as f:
            lines = [l.rstrip() for l in f]
            info_part = '\n'.join([l for l in lines if not l.startswith('char ')])
            resource['font_size'] = int(re.search(r"\ssize=(\d+)", info_part).groups()[0])
            resource['line_height'] = int(re.search(r"\slineHeight=(\d+)", info_part).groups()[0])
            resource['symbols_amount'] = int(re.search(r"\scount=(\d+)", info_part).groups()[0])
            glyph_def_lines = [l for l in lines if l.startswith('char ')]
            assert len(glyph_def_lines) == resource['symbols_amount']
            resource['definitions'] = []
            for i, glyph_def in enumerate(glyph_def_lines):
                m = re.search(r"char\sid=(\d+).*\sx=(\d+).*\sy=(\d+).*\swidth=(\d+).*\sheight=(\d+).*\sxoffset=(-?\d+).*\syoffset=(-?\d+).*\sxadvance=(-?\d+).*",
                    glyph_def)
                if not m:
                    continue
                values = [int(x) for x in m.groups()]
                resource['definitions'].append({
                    'code': values[0],
                    'glyph_x': values[1],
                    'glyph_y': values[2],
                    'glyph_width': values[3],
                    'glyph_height': values[4],
                    'x_offset': values[5],
                    'y_offset': values[6],
                    'x_advance': values[7],
                })
