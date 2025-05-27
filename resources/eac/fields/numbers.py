import math
from io import BufferedReader, BytesIO
from typing import Dict

from library.context import ReadContext, WriteContext
from library.read_blocks import IntegerBlock, DataBlock


class AngleBlock:
    def wrap_angle(self, value):
        while value >= 2 * math.pi:
            value -= math.pi * 2
        while value < 0:
            value += math.pi * 2
        return value


class Nfs1Angle8(AngleBlock, IntegerBlock):
    @property
    def schema(self) -> Dict:
        super_schema = super().schema
        return {
            **super_schema,
            'min_value': float(math.pi * 2 * super_schema['min_value'] / 256),
            'max_value': float(math.pi * 2 * super_schema['max_value'] / 256),
            'value_interval': float(math.pi * 2 * super_schema['value_interval'] / 256),
            'block_description': 'EA games 8-bit angle. 0 means 0 degrees, 0x100 (max value + 1) means 360 degrees',
        }

    def __init__(self, **kwargs):
        super().__init__(length=1, is_signed=False, **kwargs)

    def read(self, buffer: [BufferedReader, BytesIO], ctx: ReadContext = DataBlock.root_read_ctx, name: str = '',
             read_bytes_amount=None):
        return float((super().read(buffer, ctx, name, read_bytes_amount) / 256) * (math.pi * 2))

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        value = self.wrap_angle(data)
        value = min(round(256 * value / (math.pi * 2)), 0xFF)
        return super().write(value, ctx, name)


class Nfs1Angle14(AngleBlock, IntegerBlock):
    @property
    def schema(self) -> Dict:
        super_schema = super().schema
        return {
            **super_schema,
            'min_value': float(math.pi * 2 * (super_schema['min_value'] & 0x3FFF) / 0x4000),
            'max_value': float(math.pi * 2 * (super_schema['max_value'] & 0x3FFF) / 0x4000),
            'value_interval': float(math.pi * 2 * (super_schema['value_interval'] & 0x3FFF) / 0x4000),
            'block_description': 'EA games 14-bit angle (little-endian), where first 2 bits unused or have unknown'
                                 ' data. 0 means 0 degrees, 0x4000 (max value + 1) means 360 degrees',
        }

    def __init__(self, **kwargs):
        super().__init__(length=2, byte_order='little', is_signed=False, **kwargs)

    def read(self, buffer: [BufferedReader, BytesIO], ctx: ReadContext = DataBlock.root_read_ctx, name: str = '',
             read_bytes_amount=None):
        return float(((super().read(buffer, ctx, name, read_bytes_amount) & 0x3FFF) / 0x4000) * (math.pi * 2))

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        value = self.wrap_angle(data)
        value = min(round(0x4000 * value / (math.pi * 2)), 0x3FFF)
        return super().write(value, ctx, name)


class Nfs1TimeField(IntegerBlock):

    @property
    def schema(self) -> Dict:
        super_schema = super().schema
        return {
            **super_schema,
            'min_value': float(super_schema['min_value'] / 60),
            'max_value': float(super_schema['max_value'] / 60),
            'value_interval': float(super_schema['value_interval'] / 60),
            'block_description': f'TNFS time field. {super_schema["block_description"]}, '
                                 'equals to amount of ticks (amount of seconds * 60)'}

    def read(self, buffer: [BufferedReader, BytesIO], ctx: ReadContext = DataBlock.root_read_ctx, name: str = '',
             read_bytes_amount=None):
        return float(super().read(buffer, ctx, name, read_bytes_amount)) / 60

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        return super().write(int(data * 60), ctx, name)
