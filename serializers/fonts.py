import os

from library.read_data import ReadData
from resources.eac.fonts import FfnFont
from serializers import BaseFileSerializer, BitmapSerializer


class FfnFontSerializer(BaseFileSerializer):

    def serialize(self, data: ReadData[FfnFont], path: str):
        super().serialize(data, path, is_dir=True)
        image_serializer = BitmapSerializer()
        image_serializer.serialize(data.bitmap, os.path.join(path, 'bitmap'))
        with open(os.path.join(path, 'font.fnt'), 'w') as file:
            file.write(f'info face="{data.id.split("/")[-1]}" size=24\n')
            file.write('common lineHeight=32\n')
            file.write(f'page id=0 file="bitmap.png"\n')
            file.write(f'chars count={data.symbols_amount.value}\n')
            for symbol in data.definitions:
                file.write(f'char id={symbol.code.value}    x={symbol.glyph_x.value}     y={symbol.glyph_y.value}     '
                           f'width={symbol.glyph_width.value}    height={symbol.glyph_height.value}   '
                           f'xoffset={symbol.x_offset.value}     yoffset={symbol.y_offset.value}     '
                           f'xadvance={symbol.x_advance.value}    page=0  chnl=0\n')
