from library.read_blocks.atomic import IntegerBlock
from library.read_data import ReadData
from library.utils import transform_bitness, transform_color_bitness


class Color24BitDosBlock(IntegerBlock):
    def __init__(self, **kwargs):
        kwargs.pop('static_size', None)
        kwargs.pop('byte_order', None)
        super().__init__(static_size=3, byte_order="big", **kwargs)
        self.block_description = 'EA games 24-bit dos color, 00rrrrrr_00gggggg_00bbbbbb'

    def from_raw_value(self, raw: bytes, state: dict):
        number = super().from_raw_value(raw, state)
        red = transform_bitness((number & 0xFF0000) >> 16, 6)
        green = transform_bitness((number & 0xFF00) >> 8, 6)
        blue = transform_bitness(number & 0xFF, 6)
        return red << 24 | green << 16 | blue << 8 | 255

    def to_raw_value(self, data: ReadData) -> bytes:
        value = self.unwrap_result(data)
        red = (value & 0xff000000) >> 26
        green = (value & 0xff0000) >> 18
        blue = (value & 0xff00) >> 10
        value = red << 16 | green << 8 | blue
        return super().to_raw_value(self.wrap_result(value, data.block_state))


class Color24BitBlock(IntegerBlock):
    def __init__(self, **kwargs):
        kwargs.pop('static_size', None)
        super().__init__(static_size=3, **kwargs)
        self.block_description = f'EA games 24-bit color ({self.byte_order}-endian), rrrrrrrr_gggggggg_bbbbbbbb'

    def from_raw_value(self, raw: bytes, state: dict):
        number = super().from_raw_value(raw, state)
        return number << 8 | 0xFF

    def to_raw_value(self, data: ReadData) -> bytes:
        return super().to_raw_value(self.wrap_result(self.unwrap_result(data) >> 8, data.block_state))


class Color24BitBigEndianField(Color24BitBlock):
    def __init__(self, **kwargs):
        kwargs.pop('byte_order', None)
        super().__init__(byte_order="big", **kwargs)


class Color24BitLittleEndianField(Color24BitBlock):
    def __init__(self, **kwargs):
        kwargs.pop('byte_order', None)
        super().__init__(byte_order="little", **kwargs)


class Color32BitBlock(IntegerBlock):
    def __init__(self, **kwargs):
        kwargs.pop('static_size', None)
        kwargs.pop('byte_order', None)
        super().__init__(static_size=4, byte_order="little", **kwargs)
        self.block_description = 'EA games 32-bit ARGB color, aaaaaaaa_rrrrrrrr_gggggggg_bbbbbbbb'

    def get_size(self, state):
        return 4

    def from_raw_value(self, raw: bytes, state: dict):
        number = super().from_raw_value(raw, state)
        # ARGB => RGBA
        return (number & 0x00_ff_ff_ff) << 8 | (number & 0xff_00_00_00) >> 24

    def to_raw_value(self, data: ReadData) -> bytes:
        # RGBA => ARGB
        value = self.unwrap_result(data)
        value = (value & 0xff_ff_ff_00) >> 8 | (value & 0xff) << 24
        return super().to_raw_value(self.wrap_result(value))


class Color16Bit0565Block(IntegerBlock):

    # Tested on NFS2 tracks
    transparent_color = 0x00_FB_00_FF

    def __init__(self, **kwargs):
        kwargs.pop('static_size', None)
        kwargs.pop('byte_order', None)
        super().__init__(static_size=2, byte_order="little", **kwargs)
        self.block_description = 'EA games 16-bit 0565 color, rrrrrggg_gggbbbbb. 0x7c0 (0x00FB00 RGB) is always transparent'

    def from_raw_value(self, raw: bytes, state: dict):
        number = super().from_raw_value(raw, state)
        value = transform_color_bitness(number, 0, 5, 6, 5)
        if value == self.transparent_color:
            value = 0
        return value

    def to_raw_value(self, data: ReadData) -> bytes:
        value = self.unwrap_result(data)
        if (value & 0xff) < 128:
            value = self.transparent_color
        red = (value & 0xff000000) >> 27
        green = (value & 0xff0000) >> 18
        blue = (value & 0xff00) >> 11
        value = red << 11 | green << 5 | blue
        return super().to_raw_value(self.wrap_result(value, data.block_state))


class Color16Bit1555Block(IntegerBlock):
    def __init__(self, **kwargs):
        kwargs.pop('static_size', None)
        kwargs.pop('byte_order', None)
        super().__init__(static_size=2, byte_order="little", **kwargs)
        self.block_description = 'EA games 16-bit 1555 color, arrrrrgg_gggbbbbb'

    def from_raw_value(self, raw: bytes, state: dict):
        number = super().from_raw_value(raw, state)
        return transform_color_bitness(number, 1, 5, 5, 5)

    def to_raw_value(self, data: ReadData) -> bytes:
        value = self.unwrap_result(data)
        red = (value & 0xff000000) >> 27
        green = (value & 0xff0000) >> 18
        blue = (value & 0xff00) >> 11
        alpha = value & 0xff >> 7
        value = alpha << 15 | red << 10 | green << 5 | blue
        return super().to_raw_value(self.wrap_result(value, data.block_state))
