import os

from library.read_data import ReadData
from resources.eac.fonts import FfnFont
from serializers import BaseFileSerializer, BitmapSerializer


class FfnFontSerializer(BaseFileSerializer):

    def setup_for_reversible_serialization(self) -> bool:
        self.patch_settings({
            'export_unknown_values': True,
        })
        return True

    def serialize(self, data: ReadData[FfnFont], path: str):
        super().serialize(data, path, is_dir=True)
        image_serializer = BitmapSerializer()
        image_serializer.serialize(data.bitmap, os.path.join(path, 'bitmap'))
        with open(os.path.join(path, 'font.fnt'), 'w') as file:
            file.write(f'info face="{data.id.split("/")[-1]}" size={data.font_size.value}\n')
            file.write(f'common lineHeight={data.line_height.value}\n')
            file.write(f'page id=0 file="bitmap.png"\n')
            file.write(f'chars count={data.symbols_amount.value}\n')
            for symbol in data.definitions:
                file.write(f'char id={symbol.code.value}    x={symbol.glyph_x.value}     y={symbol.glyph_y.value}     '
                           f'width={symbol.glyph_width.value}    height={symbol.glyph_height.value}   '
                           f'xoffset={symbol.x_offset.value}     yoffset={symbol.y_offset.value}     '
                           f'xadvance={symbol.x_advance.value}    page=0  chnl=0\n')

    def deserialize(self, path: str, resource: ReadData, **kwargs) -> None:
        import re
        image_serializer = BitmapSerializer()
        image_serializer.deserialize(os.path.join(path, 'bitmap'), resource.bitmap)
        with open(os.path.join(path, 'font.fnt')) as f:
            lines = [l.rstrip() for l in f]
            info_part = '\n'.join([l for l in lines if not l.startswith('char ')])
            resource.font_size.value = int(re.search(r"\ssize=(\d+)", info_part).groups()[0])
            resource.line_height.value = int(re.search(r"\slineHeight=(\d+)", info_part).groups()[0])
            resource.symbols_amount.value = int(re.search(r"\scount=(\d+)", info_part).groups()[0])
            glyph_def_lines = [l for l in lines if l.startswith('char ')]
            assert len(glyph_def_lines) == resource.symbols_amount.value
            resource.definitions.value = []
            from resources.eac.fonts import SymbolDefinitionRecord
            from library.helpers.data_wrapper import DataWrapper

            glyph_block = SymbolDefinitionRecord()
            for i, glyph_def in enumerate(glyph_def_lines):
                m = re.search(r"char\sid=(\d+).*\sx=(\d+).*\sy=(\d+).*\swidth=(\d+).*\sheight=(\d+).*\sxoffset=(-?\d+).*\syoffset=(-?\d+).*\sxadvance=(-?\d+).*",
                    glyph_def)
                if not m:
                    continue
                values = [int(x) for x in m.groups()]
                # TODO remove when coming up with new way to create blocks from scratch
                rec_id = resource.definitions.id + '/' + str(i)
                resource.definitions.value.append(
                    ReadData(block=glyph_block,
                             block_state={'id': rec_id},
                             value=DataWrapper({
                                 'code': ReadData(value=values[0],
                                                  block=glyph_block.instance_fields_map['code'],
                                                  block_state={'id': rec_id + '/code'}),
                                 'glyph_x': ReadData(value=values[1],
                                                     block=glyph_block.instance_fields_map['glyph_x'],
                                                     block_state={'id': rec_id + '/glyph_x'}),
                                 'glyph_y': ReadData(value=values[2],
                                                     block=glyph_block.instance_fields_map['glyph_y'],
                                                     block_state={'id': rec_id + '/glyph_y'}),
                                 'glyph_width': ReadData(value=values[3],
                                                     block=glyph_block.instance_fields_map['glyph_width'],
                                                     block_state={'id': rec_id + '/glyph_width'}),
                                 'glyph_height': ReadData(value=values[4],
                                                     block=glyph_block.instance_fields_map['glyph_height'],
                                                     block_state={'id': rec_id + '/glyph_height'}),
                                 'x_offset': ReadData(value=values[5],
                                                     block=glyph_block.instance_fields_map['x_offset'],
                                                     block_state={'id': rec_id + '/x_offset'}),
                                 'y_offset': ReadData(value=values[6],
                                                      block=glyph_block.instance_fields_map['y_offset'],
                                                      block_state={'id': rec_id + '/y_offset'}),
                                 'x_advance': ReadData(value=values[7],
                                                      block=glyph_block.instance_fields_map['x_advance'],
                                                      block_state={'id': rec_id + '/x_advance'}),
                             }))
                )
