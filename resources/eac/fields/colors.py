from library.read_blocks.atomic import IntegerBlock
from library.read_data import ReadData
from library.utils import transform_bitness, transform_color_bitness


class Color24BitDosBlock(IntegerBlock):
    def __init__(self, **kwargs):
        super().__init__(static_size=3, byte_order="big", **kwargs)
        self.block_description = 'EA games 24-bit dos color, 00rrrrrr_00gggggg_00bbbbbb'

    def from_raw_value(self, raw: bytes, state: dict):
        number = super().from_raw_value(raw, state)
        red = transform_bitness((number & 0xFF0000) >> 16, 6)
        green = transform_bitness((number & 0xFF00) >> 8, 6)
        blue = transform_bitness(number & 0xFF, 6)
        return red << 24 | green << 16 | blue << 8 | 255

    def to_raw_value(self, data: ReadData, state) -> bytes:
        red = (data.value & 0xff000000) >> 26
        green = (data.value & 0xff0000) >> 18
        blue = (data.value & 0xff00) >> 10
        data.value = red << 16 | green << 8 | blue
        return super().to_raw_value(data, state)


class Color24BitBlock(IntegerBlock):
    def __init__(self, **kwargs):
        super().__init__(static_size=3, **kwargs)
        self.block_description = f'EA games 24-bit color ({self.byte_order}-endian), rrrrrrrr_gggggggg_bbbbbbbb'

    def from_raw_value(self, raw: bytes, state: dict):
        number = super().from_raw_value(raw, state)
        return number << 8 | 0xFF

    def to_raw_value(self, data: ReadData, state) -> bytes:
        data.value = data.value >> 8
        return super().to_raw_value(data, state)


class Color24BitBigEndianField(Color24BitBlock):
    def __init__(self, **kwargs):
        super().__init__(byte_order="big", **kwargs)


class Color24BitLittleEndianField(Color24BitBlock):
    def __init__(self, **kwargs):
        super().__init__(byte_order="little", **kwargs)


class Color32BitBlock(IntegerBlock):
    def __init__(self, **kwargs):
        super().__init__(static_size=4, byte_order="little", **kwargs)
        self.block_description = 'EA games 32-bit ARGB color, aaaaaaaa_rrrrrrrr_gggggggg_bbbbbbbb'

    def get_size(self, state):
        return 4

    def from_raw_value(self, raw: bytes, state: dict):
        number = super().from_raw_value(raw, state)
        # ARGB => RGBA
        return (number & 0x00_ff_ff_ff) << 8 | (number & 0xff_00_00_00) >> 24

    def to_raw_value(self, data: ReadData, state) -> bytes:
        # RGBA => ARGB
        data.value = (data.value & 0xff_ff_ff_00) >> 8 | (data.value & 0xff) << 24
        return super().to_raw_value(data, state)


class Color16Bit0565Block(IntegerBlock):

    # Tested on NFS2 tracks
    transparent_color = 0x00_FB_00_FF

    def __init__(self, **kwargs):
        super().__init__(static_size=2, byte_order="little", **kwargs)
        self.block_description = 'EA games 16-bit 0565 color, rrrrrggg_gggbbbbb. 0x7c0 (0x00FB00 RGB) is always transparent'

    def from_raw_value(self, raw: bytes, state: dict):
        number = super().from_raw_value(raw, state)
        value = transform_color_bitness(number, 0, 5, 6, 5)
        if value == self.transparent_color:
            value = 0
        return value

    def to_raw_value(self, data: ReadData, state) -> bytes:
        if (data.value & 0xff) < 128:
            data = self.transparent_color
        red = (data.value & 0xff000000) >> 27
        green = (data.value & 0xff0000) >> 18
        blue = (data.value & 0xff00) >> 11
        data.value = red << 11 | green << 5 | blue
        return super().to_raw_value(data, state)


class Color16Bit1555Block(IntegerBlock):
    def __init__(self, **kwargs):
        super().__init__(static_size=2, byte_order="little", **kwargs)
        self.block_description = 'EA games 16-bit 1555 color, arrrrrgg_gggbbbbb'

    def from_raw_value(self, raw: bytes, state: dict):
        number = super().from_raw_value(raw, state)
        return transform_color_bitness(number, 1, 5, 5, 5)

    def to_raw_value(self, data: ReadData, state) -> bytes:
        red = (data.value & 0xff000000) >> 27
        green = (data.value & 0xff0000) >> 18
        blue = (data.value & 0xff00) >> 11
        alpha = data.value & 0xff >> 7
        data.value = alpha << 15 | red << 10 | green << 5 | blue
        return super().to_raw_value(data, state)
