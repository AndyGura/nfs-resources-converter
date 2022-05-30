import json
import os
from io import BufferedReader, SEEK_CUR

from PIL import Image

from buffer_utils import read_utf_bytes, read_int, read_short, read_byte, read_signed_byte
from parsers.resources.base import BaseResource
from parsers.resources.utils import transform_bitness


class FfnFont(BaseResource):
    bit_data = []
    width = 0
    height = 0
    symbols = []

    # Structure
    # 0x0000: 4-bytes UTF header string 'FNTF'
    # 0x0004: 4-bytes file size
    # 0x0008: 2-bytes (always 100?)
    # 0x000A: 2-bytes symbols amount N
    # 0x000C: 16-bytes unknown data
    # 0x001C: 2-bytes pointer to 7A 00 00 00
    # 0x001E: 2-bytes unknown
    # 0x0020: start of N symbol records. Each record has size 11 bytes
    # M*0xB + 0x0020: 4-bytes AD AD AD AD (optional, happens in nfs2 SWISS36)!!! TODO why? probably has some reason
    # M*0xB + 0x0024: 7A 00 00 00
    # M*0xB + 0x0028: 2-bytes bitmap width
    # M*0xB + 0x002A: 2-bytes bitmap height
    # M*0xB + 0x002C: 8-bytes unknown data
    # M*0xB + 0x0034: grayscale 4-bit bitmap data. Every byte is two pixels

    def read(self, buffer: BufferedReader, length: int, path: str = None) -> int:
        header = read_utf_bytes(buffer, 4)
        assert header == 'FNTF', Exception('Unexpected FFN file header string')
        ffn_size = read_int(buffer)
        assert ffn_size <= length, Exception(f'Unexpected FFN file length. Actual file is {length}, in header {ffn_size}')
        unk = read_short(buffer) # always 100?
        assert unk == 100, NotImplementedError('Unknown FFN file')
        symbols_amount = read_short(buffer)
        buffer.seek(16, SEEK_CUR)
        bitmap_data_start = read_short(buffer)
        buffer.seek(2, SEEK_CUR)
        for i in range(symbols_amount):
            code = read_short(buffer)
            width = read_byte(buffer)
            height = read_byte(buffer)
            x = read_short(buffer)
            y = read_short(buffer)
            x_advance = read_byte(buffer)
            x_offset = read_signed_byte(buffer)
            y_offset = read_signed_byte(buffer)
            self.symbols.append({
                'code': code,
                'symbol': chr(code),
                'width': width,
                'height': height,
                'x': x,
                'y': y,
                'x_offset': x_offset,
                'y_offset': y_offset,
                'x_advance': x_advance,
            })
        if buffer.tell() != bitmap_data_start:
            buffer.seek(4, SEEK_CUR)
        assert buffer.tell() == bitmap_data_start, Exception('Unexpected FFN file structure')
        buffer.seek(4, SEEK_CUR)
        self.width = read_short(buffer)
        self.height = read_short(buffer)
        buffer.seek(8, SEEK_CUR)
        self.bit_data = [x for x in buffer.read(ffn_size - buffer.tell())]
        return length

    def save_converted(self, path: str):
        if not os.path.exists(path):
            os.makedirs(path)
        data = [transform_bitness(item, 4) for sublist in [[(x & 0xf0) >> 4, x & 0xf] for x in self.bit_data] for item in sublist]
        colors = [0xffffff00 | x for x in data]
        if len(colors) < self.width * self.height:
            colors += [0xffffff00] * (self.width * self.height - len(colors))
        img = Image.frombytes('RGBA', (self.width, self.height), bytes().join([c.to_bytes(4, 'big') for c in colors]))
        img.save(f'{path}/bitmap.png')
        with open(f'{path}/font.fnt', 'w') as file:
            file.write(f'info face="{self.name}" size=24\n')
            file.write('common lineHeight=32\n')
            file.write(f'page id=0 file="bitmap.png"\n')
            file.write(f'chars count={len(self.symbols)}\n')
            for symbol in self.symbols:
                file.write(f'char id={symbol["code"]}    x={symbol["x"]}     y={symbol["y"]}     width={symbol["width"]}    height={symbol["height"]}   xoffset={symbol["x_offset"]}     yoffset={symbol["y_offset"]}     xadvance={symbol["x_advance"]}    page=0  chnl=0\n')
        # for symbol in self.symbols:
        #     try:
        #         img.crop((symbol['x'], symbol['y'], symbol['x'] + symbol['width'], symbol['y'] + symbol['height'])).save(f'{path}/glyph_{symbol["symbol"]}.png')
        #     except:
        #         img.crop((symbol['x'], symbol['y'], symbol['x'] + symbol['width'], symbol['y'] + symbol['height'])).save(f'{path}/glyph_{symbol["code"]}.png')

