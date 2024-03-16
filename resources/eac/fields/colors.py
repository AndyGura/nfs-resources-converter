from io import BufferedReader, BytesIO
from typing import Dict

from library.context import ReadContext, WriteContext
from library.read_blocks import IntegerBlock, DataBlock
from library.utils import transform_bitness, transform_color_bitness


class Color24BitDosBlock(IntegerBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'EA games 24-bit dos color, 00rrrrrr_00gggggg_00bbbbbb',
        }

    def __init__(self, **kwargs):
        super().__init__(length=3, byte_order="big", **kwargs)

    def read(self, buffer: [BufferedReader, BytesIO], ctx: ReadContext = DataBlock.root_read_ctx, name: str = '',
             read_bytes_amount=None):
        number = super().read(buffer, ctx, name)
        red = transform_bitness((number & 0xFF0000) >> 16, 6)
        green = transform_bitness((number & 0xFF00) >> 8, 6)
        blue = transform_bitness(number & 0xFF, 6)
        return red << 24 | green << 16 | blue << 8 | 255

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        red = (data & 0xff000000) >> 26
        green = (data & 0xff0000) >> 18
        blue = (data & 0xff00) >> 10
        value = red << 16 | green << 8 | blue
        return super().write(value, ctx, name)


class Color24BitBlock(IntegerBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': f'EA games 24-bit color ({self.byte_order}-endian), rrrrrrrr_gggggggg_bbbbbbbb',
        }

    def __init__(self, **kwargs):
        super().__init__(length=3, **kwargs)

    def read(self, buffer: [BufferedReader, BytesIO], ctx: ReadContext = DataBlock.root_read_ctx, name: str = '',
             read_bytes_amount=None):
        number = super().read(buffer, ctx, name)
        return number << 8 | 0xFF

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        return super().write(data >> 8, ctx, name)


class Color24BitBigEndianField(Color24BitBlock):
    def __init__(self, **kwargs):
        super().__init__(byte_order="big", **kwargs)


class Color24BitLittleEndianField(Color24BitBlock):
    pass


class Color32BitBlock(IntegerBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'EA games 32-bit ARGB color, aaaaaaaa_rrrrrrrr_gggggggg_bbbbbbbb',
        }

    def __init__(self, **kwargs):
        super().__init__(length=4, **kwargs)

    def read(self, buffer: [BufferedReader, BytesIO], ctx: ReadContext = DataBlock.root_read_ctx, name: str = '',
             read_bytes_amount=None):
        number = super().read(buffer, ctx, name)
        # ARGB => RGBA
        return (number & 0x00_ff_ff_ff) << 8 | (number & 0xff_00_00_00) >> 24

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        # RGBA => ARGB
        return super().write((data & 0xff_ff_ff_00) >> 8 | (data & 0xff) << 24, ctx, name)


class Color16Bit0565Block(IntegerBlock):
    # Tested on NFS2 tracks
    transparent_color = 0x00_FB_00_FF

    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'EA games 16-bit 0565 color, rrrrrggg_gggbbbbb. 0x7c0 (0x00FB00 RGB) is always transparent',
        }

    def __init__(self, **kwargs):
        super().__init__(length=2, **kwargs)

    def read(self, buffer: [BufferedReader, BytesIO], ctx: ReadContext = DataBlock.root_read_ctx, name: str = '',
             read_bytes_amount=None):
        number = super().read(buffer, ctx, name)
        value = transform_color_bitness(number, 0, 5, 6, 5)
        if value == self.transparent_color:
            value = 0
        return value

    def write(self, value, ctx: WriteContext = None, name: str = '') -> bytes:
        if (value & 0xff) < 128:
            value = self.transparent_color
        red = (value & 0xff000000) >> 27
        green = (value & 0xff0000) >> 18
        blue = (value & 0xff00) >> 11
        value = red << 11 | green << 5 | blue
        return super().write(value, ctx, name)


class Color16BitDosBlock(IntegerBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': '16-bit color, not tested properly',
        }

    def __init__(self, **kwargs):
        super().__init__(length=2, **kwargs)

    # TODO colors not tested!
    def read(self, buffer: [BufferedReader, BytesIO], ctx: ReadContext = DataBlock.root_read_ctx, name: str = '',
             read_bytes_amount=None):
        number = super().read(buffer, ctx, name)
        value = transform_color_bitness(number, 0, 5, 6, 5)
        return value

    def write(self, value, ctx: WriteContext = None, name: str = '') -> bytes:
        red = (value & 0xff000000) >> 27
        green = (value & 0xff0000) >> 18
        blue = (value & 0xff00) >> 11
        value = red << 11 | green << 5 | blue
        return super().write(value, ctx, name)


class Color16Bit1555Block(IntegerBlock):

    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'EA games 16-bit 1555 color, arrrrrgg_gggbbbbb',
        }

    def __init__(self, **kwargs):
        super().__init__(length=2, **kwargs)

    def read(self, buffer: [BufferedReader, BytesIO], ctx: ReadContext = DataBlock.root_read_ctx, name: str = '',
             read_bytes_amount=None):
        number = super().read(buffer, ctx, name)
        return transform_color_bitness(number, 1, 5, 5, 5)

    def write(self, value, ctx: WriteContext = None, name: str = '') -> bytes:
        red = (value & 0xff000000) >> 27
        green = (value & 0xff0000) >> 18
        blue = (value & 0xff00) >> 11
        alpha = value & 0xff >> 7
        return super().write(alpha << 15 | red << 10 | green << 5 | blue, ctx, name)
