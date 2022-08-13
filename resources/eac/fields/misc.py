from library.helpers.data_wrapper import DataWrapper
from library.read_blocks.atomic import IntegerBlock
from library.read_blocks.compound import CompoundBlock
from library.read_data import ReadData
from resources.eac.fields.numbers import RationalNumber


class Point3D_16(CompoundBlock):
    block_description = 'Point in 3D space (x,y,z), where each coordinate is: ' \
                        + RationalNumber(static_size=2, fraction_bits=8, is_signed=True).block_description \
                        + '. The unit is meter'

    def __init__(self, **kwargs):
        kwargs['inline_description'] = True
        super().__init__(**kwargs)

    class Fields(CompoundBlock.Fields):
        x = RationalNumber(static_size=2, fraction_bits=8, is_signed=True)
        y = RationalNumber(static_size=2, fraction_bits=8, is_signed=True)
        z = RationalNumber(static_size=2, fraction_bits=8, is_signed=True)


class Point3D_16_7(CompoundBlock):
    block_description = 'Point in 3D space (x,y,z), where each coordinate is: ' \
                        + RationalNumber(static_size=2, fraction_bits=7, is_signed=True).block_description \
                        + '. The unit is meter'

    def __init__(self, **kwargs):
        kwargs['inline_description'] = True
        super().__init__(**kwargs)

    class Fields(CompoundBlock.Fields):
        x = RationalNumber(static_size=2, fraction_bits=7, is_signed=True)
        y = RationalNumber(static_size=2, fraction_bits=7, is_signed=True)
        z = RationalNumber(static_size=2, fraction_bits=7, is_signed=True)


class Point3D_32(CompoundBlock):
    block_description = 'Point in 3D space (x,y,z), where each coordinate is: ' \
                        + RationalNumber(static_size=4, fraction_bits=16, is_signed=True).block_description \
                        + '. The unit is meter'

    def __init__(self, **kwargs):
        kwargs['inline_description'] = True
        super().__init__(**kwargs)

    class Fields(CompoundBlock.Fields):
        x = RationalNumber(static_size=4, fraction_bits=16, is_signed=True)
        y = RationalNumber(static_size=4, fraction_bits=16, is_signed=True)
        z = RationalNumber(static_size=4, fraction_bits=16, is_signed=True)


class Point3D_32_4(CompoundBlock):
    block_description = 'Point in 3D space (x,y,z), where each coordinate is: ' \
                        + RationalNumber(static_size=4, fraction_bits=4, is_signed=True).block_description \
                        + '. The unit is meter'

    def __init__(self, **kwargs):
        kwargs['inline_description'] = True
        super().__init__(**kwargs)

    class Fields(CompoundBlock.Fields):
        x = RationalNumber(static_size=4, fraction_bits=4, is_signed=True)
        y = RationalNumber(static_size=4, fraction_bits=4, is_signed=True)
        z = RationalNumber(static_size=4, fraction_bits=4, is_signed=True)


class Point3D_32_7(CompoundBlock):
    block_description = 'Point in 3D space (x,y,z), where each coordinate is: ' \
                        + RationalNumber(static_size=4, fraction_bits=7, is_signed=True).block_description \
                        + '. The unit is meter'

    def __init__(self, **kwargs):
        kwargs['inline_description'] = True
        super().__init__(**kwargs)

    class Fields(CompoundBlock.Fields):
        x = RationalNumber(static_size=4, fraction_bits=7, is_signed=True)
        y = RationalNumber(static_size=4, fraction_bits=7, is_signed=True)
        z = RationalNumber(static_size=4, fraction_bits=7, is_signed=True)


class FenceType(IntegerBlock):
    def __init__(self, **kwargs):
        kwargs['static_size'] = 1
        kwargs['is_signed'] = False
        super().__init__(**kwargs)
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
