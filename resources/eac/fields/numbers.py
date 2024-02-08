import math
from io import BufferedReader, BytesIO
from typing import Dict

from library.context import ReadContext, WriteContext
from library.read_blocks import IntegerBlock


class RationalNumber(IntegerBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': f'{self.length * 8}-bit real number ({self.byte_order}-endian, '
                                 f'{"" if self.is_signed else "not "}signed), where last {self.fraction_bits} '
                                 f'bits is a fractional part',
            # TODO min_value max_value value_interval
        }

    def __init__(self, fraction_bits: int, **kwargs):
        super().__init__(**kwargs)
        self.fraction_bits = fraction_bits

    def read(self, buffer: [BufferedReader, BytesIO], ctx: ReadContext = None, name: str = '', read_bytes_amount=None):
        return float(super().read(buffer, ctx, name, read_bytes_amount) / (1 << self.fraction_bits))

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        data = max(min(round(data * (1 << self.fraction_bits)),
                       ((1 << (self.length * 8 - 1)) if self.is_signed else (1 << (self.length * 8))) - 1),
                   -(1 << (self.length * 8 - 1)) if self.is_signed else 0)
        return super().write(data, ctx, name)


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
        return {
            **super().schema,
            'block_description': 'EA games 8-bit angle. 0 means 0 degrees, 0x100 (max value + 1) means 360 degrees',
        }

    def __init__(self, **kwargs):
        super().__init__(length=1, is_signed=False, **kwargs)

    def read(self, buffer: [BufferedReader, BytesIO], ctx: ReadContext = None, name: str = '', read_bytes_amount=None):
        return float((super().read(buffer, ctx, name, read_bytes_amount) / 256) * (math.pi * 2))

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        value = self.wrap_angle(data)
        value = min(round(256 * value / (math.pi * 2)), 0xFF)
        return super().write(value, ctx, name)


class Nfs1Angle14(AngleBlock, IntegerBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'EA games 14-bit angle (little-endian), where first 2 bits unused or have unknown'
                                 ' data. 0 means 0 degrees, 0x4000 (max value + 1) means 360 degrees',
        }

    def __init__(self, **kwargs):
        super().__init__(length=2, byte_order='little', is_signed=False, **kwargs)

    def read(self, buffer: [BufferedReader, BytesIO], ctx: ReadContext = None, name: str = '', read_bytes_amount=None):
        return float(((super().read(buffer, ctx, name, read_bytes_amount) & 0x3FFF) / 0x4000) * (math.pi * 2))

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        value = self.wrap_angle(data)
        value = min(round(0x4000 * value / (math.pi * 2)), 0x3FFF)
        return super().write(value, ctx, name)


class Nfs1Angle16(AngleBlock, IntegerBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'EA games 16-bit angle (little-endian). 0 means 0 degrees, 0x10000 (max value + 1) ' \
                                 'means 360 degrees',
        }

    def __init__(self, **kwargs):
        super().__init__(length=2, byte_order='little', is_signed=False, **kwargs)

    def read(self, buffer: [BufferedReader, BytesIO], ctx: ReadContext = None, name: str = '', read_bytes_amount=None):
        return float((super().read(buffer, ctx, name, read_bytes_amount) / 0x10000) * (math.pi * 2))

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        value = self.wrap_angle(data)
        value = min(round(0x10000 * value / (math.pi * 2)), 0xFFFF)
        return super().write(value, ctx, name)


class Nfs1TimeField(IntegerBlock):

    @property
    def schema(self) -> Dict:
        return {**super().schema,
                'block_description': f'TNFS time field. {super().schema["block_description"]}, '
                                     'equals to amount of ticks (amount of seconds * 60)'}

    def read(self, buffer: [BufferedReader, BytesIO], ctx: ReadContext = None, name: str = '', read_bytes_amount=None):
        return float(super().read(buffer, ctx, name, read_bytes_amount)) / 60

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        return super().write(int(data * 60), ctx, name)
