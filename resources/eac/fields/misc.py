from library.helpers.data_wrapper import DataWrapper
from library.read_blocks.atomic import IntegerBlock, Utf8Block
from library.read_blocks.compound import CompoundBlock
from library.read_data import ReadData
from resources.eac.fields.numbers import RationalNumber


class Nfs1Utf8Block(Utf8Block):

    def __init__(self, *args, **kwargs):
        super().__init__(pad_value=0, **kwargs)
        self.block_description = 'NFS1 UTF-8 string with variable length, but static size in file. 0x00 means end of string, the rest is ignored'

    def from_raw_value(self, raw: bytes, state: dict):
        try:
            raw = raw[:raw.index(0)]
        except ValueError:
            pass
        # In NFS1 sometimes we can see sequences, which cannot be parsed as UTF-8, for instance, 0x80 0x02 Ignore them
        return raw.decode('utf-8', errors='ignore')


class Point3D_16(CompoundBlock):
    block_description = 'Point in 3D space (x,y,z), where each coordinate is: ' \
                        + RationalNumber(static_size=2, fraction_bits=8, is_signed=True).block_description \
                        + '. The unit is meter'

    def __init__(self, **kwargs):
        kwargs.pop('inline_description', None)
        super().__init__(inline_description=True, **kwargs)

    class Fields(CompoundBlock.Fields):
        x = RationalNumber(static_size=2, fraction_bits=8, is_signed=True)
        y = RationalNumber(static_size=2, fraction_bits=8, is_signed=True)
        z = RationalNumber(static_size=2, fraction_bits=8, is_signed=True)


class Point3D_16_7(CompoundBlock):
    block_description = 'Point in 3D space (x,y,z), where each coordinate is: ' \
                        + RationalNumber(static_size=2, fraction_bits=7, is_signed=True).block_description \
                        + '. The unit is meter'

    def __init__(self, **kwargs):
        kwargs.pop('inline_description', None)
        super().__init__(inline_description=True, **kwargs)

    class Fields(CompoundBlock.Fields):
        x = RationalNumber(static_size=2, fraction_bits=7, is_signed=True)
        y = RationalNumber(static_size=2, fraction_bits=7, is_signed=True)
        z = RationalNumber(static_size=2, fraction_bits=7, is_signed=True)


class Point3D_32(CompoundBlock):
    block_description = 'Point in 3D space (x,y,z), where each coordinate is: ' \
                        + RationalNumber(static_size=4, fraction_bits=16, is_signed=True).block_description \
                        + '. The unit is meter'

    def __init__(self, **kwargs):
        kwargs.pop('inline_description', None)
        super().__init__(inline_description=True, **kwargs)

    class Fields(CompoundBlock.Fields):
        x = RationalNumber(static_size=4, fraction_bits=16, is_signed=True)
        y = RationalNumber(static_size=4, fraction_bits=16, is_signed=True)
        z = RationalNumber(static_size=4, fraction_bits=16, is_signed=True)


class Point3D_32_4(CompoundBlock):
    block_description = 'Point in 3D space (x,y,z), where each coordinate is: ' \
                        + RationalNumber(static_size=4, fraction_bits=4, is_signed=True).block_description \
                        + '. The unit is meter'

    def __init__(self, **kwargs):
        kwargs.pop('inline_description', None)
        super().__init__(inline_description=True, **kwargs)

    class Fields(CompoundBlock.Fields):
        x = RationalNumber(static_size=4, fraction_bits=4, is_signed=True)
        y = RationalNumber(static_size=4, fraction_bits=4, is_signed=True)
        z = RationalNumber(static_size=4, fraction_bits=4, is_signed=True)


class Point3D_32_7(CompoundBlock):
    block_description = 'Point in 3D space (x,y,z), where each coordinate is: ' \
                        + RationalNumber(static_size=4, fraction_bits=7, is_signed=True).block_description \
                        + '. The unit is meter'

    def __init__(self, **kwargs):
        kwargs.pop('inline_description', None)
        super().__init__(inline_description=True, **kwargs)

    class Fields(CompoundBlock.Fields):
        x = RationalNumber(static_size=4, fraction_bits=7, is_signed=True)
        y = RationalNumber(static_size=4, fraction_bits=7, is_signed=True)
        z = RationalNumber(static_size=4, fraction_bits=7, is_signed=True)


class FenceType(IntegerBlock):
    def __init__(self, **kwargs):
        kwargs.pop('static_size', None)
        kwargs.pop('is_signed', None)
        super().__init__(static_size=1, is_signed=False, **kwargs)
        self.block_description = 'TNFS fence type field. fence type: [lrtttttt]' \
                                 '<br/>l - flag is add left fence' \
                                 '<br/>r - flag is add right fence' \
                                 '<br/>tttttt - texture id'

    def from_raw_value(self, raw: bytes, state: dict):
        fence_type = super().from_raw_value(raw, state)
        return DataWrapper({
            'texture_id': fence_type & (0xff >> 2),
            'has_left_fence': (fence_type & (0x1 << 7)) != 0,
            'has_right_fence': (fence_type & (0x1 << 6)) != 0,
        })

    def to_raw_value(self, data: ReadData) -> bytes:
        value = self.unwrap_result(data)
        byte = value['texture_id'] & (0xff >> 2)
        if value['has_left_fence']:
            byte = byte | (0x1 << 7)
        if value['has_right_fence']:
            byte = byte | (0x1 << 6)
        return super().to_raw_value(self.wrap_result(byte, data.block_state))
