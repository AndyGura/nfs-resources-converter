from io import BufferedReader, BytesIO
from typing import Dict

from library.context import WriteContext, ReadContext
from library.read_blocks import IntegerBlock, DataBlock, CompoundBlock
from resources.eac.fields.numbers import RationalNumber


class Point3D(CompoundBlock):

    @property
    def schema(self) -> Dict:
        schema = super().schema
        return {
            **super().schema,
            'block_description': 'Point in 3D space (x,y,z), where each coordinate is: '
                                 + schema['fields'][0]['schema']['block_description'],
            'inline_description': True,
        }

    def __init__(self, child_length, fraction_bits=0, is_signed=True, **kwargs):
        child = RationalNumber(length=child_length, fraction_bits=fraction_bits, is_signed=is_signed)
        super().__init__(fields=[('x', child, {}),
                                 ('y', child, {}),
                                 ('z', child, {})], **kwargs)


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

    def read(self, buffer: [BufferedReader, BytesIO], ctx: ReadContext = DataBlock.root_read_ctx, name: str = '',
             read_bytes_amount=None):
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
