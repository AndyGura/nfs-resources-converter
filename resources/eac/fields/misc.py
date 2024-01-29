from io import BufferedReader, BytesIO
from typing import Dict

from library2.context import WriteContext, ReadContext
from library2.read_blocks import DeclarativeCompoundBlock, IntegerBlock
from resources.eac.fields.numbers import RationalNumber


class Point3D_16(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Point in 3D space (x,y,z), where each coordinate is: '
                                 + RationalNumber(length=2, fraction_bits=8, is_signed=True).schema['block_description']
                                 + '. The unit is meter',
            'inline_description': True,
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        x = RationalNumber(length=2, fraction_bits=8, is_signed=True)
        y = RationalNumber(length=2, fraction_bits=8, is_signed=True)
        z = RationalNumber(length=2, fraction_bits=8, is_signed=True)


class Point3D_16_7(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Point in 3D space (x,y,z), where each coordinate is: '
                                 + RationalNumber(length=2, fraction_bits=7, is_signed=True).schema['block_description']
                                 + '. The unit is meter',
            'inline_description': True,
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        x = RationalNumber(length=2, fraction_bits=7, is_signed=True)
        y = RationalNumber(length=2, fraction_bits=7, is_signed=True)
        z = RationalNumber(length=2, fraction_bits=7, is_signed=True)


class Point3D_32(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Point in 3D space (x,y,z), where each coordinate is: '
                                 + RationalNumber(length=4, fraction_bits=16, is_signed=True).schema[
                                     'block_description']
                                 + '. The unit is meter',
            'inline_description': True,
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        x = RationalNumber(length=4, fraction_bits=16, is_signed=True)
        y = RationalNumber(length=4, fraction_bits=16, is_signed=True)
        z = RationalNumber(length=4, fraction_bits=16, is_signed=True)


class Point3D_32_4(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Point in 3D space (x,y,z), where each coordinate is: '
                                 + RationalNumber(length=4, fraction_bits=4, is_signed=True).schema['block_description']
                                 + '. The unit is meter',
            'inline_description': True,
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        x = RationalNumber(length=4, fraction_bits=4, is_signed=True)
        y = RationalNumber(length=4, fraction_bits=4, is_signed=True)
        z = RationalNumber(length=4, fraction_bits=4, is_signed=True)


class Point3D_32_7(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Point in 3D space (x,y,z), where each coordinate is: '
                                 + RationalNumber(length=4, fraction_bits=7, is_signed=True).schema['block_description']
                                 + '. The unit is meter',
            'inline_description': True,
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        x = RationalNumber(length=4, fraction_bits=7, is_signed=True)
        y = RationalNumber(length=4, fraction_bits=7, is_signed=True)
        z = RationalNumber(length=4, fraction_bits=7, is_signed=True)


class FenceType(IntegerBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'TNFS fence type field. fence type: [lrtttttt]'
                                 '<br/>l - flag is add left fence'
                                 '<br/>r - flag is add right fence'
                                 '<br/>tttttt - texture id',
        }

    def __init__(self, **kwargs):
        super().__init__(length=1, is_signed=False, **kwargs)

    def read(self, buffer: [BufferedReader, BytesIO], ctx: ReadContext = None, name: str = '', read_bytes_amount=None):
        fence_type = super().read(buffer, ctx, name, read_bytes_amount)
        return {
            'texture_id': fence_type & (0xff >> 2),
            'has_left_fence': (fence_type & (0x1 << 7)) != 0,
            'has_right_fence': (fence_type & (0x1 << 6)) != 0,
        }

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        byte = data['texture_id'] & (0xff >> 2)
        if data['has_left_fence']:
            byte = byte | (0x1 << 7)
        if data['has_right_fence']:
            byte = byte | (0x1 << 6)
        return super().write(byte, ctx, name)
