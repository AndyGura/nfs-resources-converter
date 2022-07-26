import os

from resources.eac.fonts import FfnFont
from serializers import BaseFileSerializer, BitmapSerializer


class FfnFontSerializer(BaseFileSerializer):

    def serialize(self, block: FfnFont, path: str):
        super().serialize(block, path)
        if not os.path.exists(path):
            os.makedirs(path)
        image_serializer = BitmapSerializer()
        image_serializer.serialize(block.bitmap, f'{path}/bitmap')
        with open(f'{path}/font.fnt', 'w') as file:
            file.write(f'info face="{block.id.split("/")[-1]}" size=24\n')
            file.write('common lineHeight=32\n')
            file.write(f'page id=0 file="bitmap.png"\n')
            file.write(f'chars count={block.symbols_amount.value}\n')
            for symbol in block.definitions:
                file.write(f'char id={symbol.code.value}    x={symbol.glyph_x.value}     y={symbol.glyph_y.value}     '
                           f'width={symbol.glyph_width.value}    height={symbol.glyph_height.value}   '
                           f'xoffset={symbol.x_offset.value}     yoffset={symbol.y_offset.value}     '
                           f'xadvance={symbol.x_advance.value}    page=0  chnl=0\n')

