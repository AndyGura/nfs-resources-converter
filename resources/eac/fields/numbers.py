import math

from library.read_blocks.atomic import IntegerBlock
from library.read_data import ReadData


class RationalNumber(IntegerBlock):
    def __init__(self, fraction_bits: int, **kwargs):
        super().__init__(**kwargs)
        self.fraction_bits = fraction_bits
        self.block_description = f'{self.static_size * 8}-bit real number ({self.byte_order}-endian, ' \
                                 f'{"" if self.is_signed else "not "}signed), where last {fraction_bits} ' \
                                 f'bits is a fractional part'

    @property
    def max_value(self):
        if self.is_signed:
            return (1 << (8 * self.static_size - 1)) - 1
        else:
            return (1 << (8 * self.static_size)) - 1

    def from_raw_value(self, raw: bytes, state: dict):
        return float(super().from_raw_value(raw, state) / (1 << self.fraction_bits))

    def to_raw_value(self, data: ReadData) -> bytes:
        value = self.unwrap_result(data)
        value = min(round(value * (1 << self.fraction_bits)), self.max_value)
        return super().to_raw_value(self.wrap_result(value, data.block_state))


class Nfs1Angle8(IntegerBlock):
    def __init__(self, **kwargs):
        kwargs.pop('static_size', None)
        kwargs.pop('is_signed', None)
        super().__init__(static_size=1, is_signed=False, **kwargs)
        self.block_description = 'EA games 8-bit angle. 0 means 0 degrees, 0x100 (max value + 1) means 360 degrees'

    def from_raw_value(self, raw: bytes, state: dict):
        return float((super().from_raw_value(raw, state) / 256) * (math.pi * 2))

    def to_raw_value(self, data: ReadData) -> bytes:
        value = self.unwrap_result(data)
        while value >= 2 * math.pi:
            value -= math.pi * 2
        while value < 0:
            value += math.pi * 2
        value = min(round(256 * value / (math.pi * 2)), 0xFF)
        return super().to_raw_value(self.wrap_result(value, data.block_state))


class Nfs1Angle14(IntegerBlock):
    def __init__(self, **kwargs):
        kwargs.pop('static_size', None)
        kwargs.pop('byte_order', None)
        kwargs.pop('is_signed', None)
        super().__init__(static_size=2, byte_order='little', is_signed=True, **kwargs)
        self.block_description = 'EA games 14-bit angle (little-endian), where first 2 bits unused or have unknown' \
                                 ' data. 0 means 0 degrees, 0x4000 (max value + 1) means 360 degrees'

    def from_raw_value(self, raw: bytes, state: dict):
        return float(((super().from_raw_value(raw, state) & 0x3FFF) / 0x4000) * (math.pi * 2))

    def to_raw_value(self, data: ReadData) -> bytes:
        value = self.unwrap_result(data)
        while value >= 2 * math.pi:
            value -= math.pi * 2
        while value < 0:
            value += math.pi * 2
        value = min(round(0x4000 * data.value / (math.pi * 2)), 0x3FFF)
        return super().to_raw_value(self.wrap_result(value, data.block_state))
