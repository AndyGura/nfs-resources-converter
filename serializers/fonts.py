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
            file.write(f'chars count={block.symbols_amount}\n')
            for symbol in block.definitions:
                file.write(f'char id={symbol.code}    x={symbol.glyph_x}     y={symbol.glyph_y}     '
                           f'width={symbol.glyph_width}    height={symbol.glyph_height}   '
                           f'xoffset={symbol.x_offset}     yoffset={symbol.y_offset}     '
                           f'xadvance={symbol.x_advance}    page=0  chnl=0\n')

