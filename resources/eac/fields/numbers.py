import math

from library.read_blocks.atomic import IntegerField


class RationalNumber(IntegerField):
    def __init__(self, fraction_bits: int, **kwargs):
        self.fraction_bits = kwargs['fraction_bits'] = fraction_bits
        super().__init__(**kwargs)
        self.block_description = f'{self.static_size * 8}-bit real number ({self.byte_order}-endian, ' \
                                 f'{"" if self.is_signed else "not "}signed), where last {fraction_bits} ' \
                                 f'bits is a fractional part'

    def from_raw_value(self, raw: bytes):
        return float(super().from_raw_value(raw) / (1 << self.fraction_bits))

    def to_raw_value(self, value) -> bytes:
        return super().to_raw_value(math.floor(value * (1 << self.fraction_bits)))


class Nfs1Angle8(IntegerField):
    def __init__(self, **kwargs):
        kwargs['static_size'] = 1
        kwargs['is_signed'] = False
        super().__init__(**kwargs)
        self.block_description = 'EA games 8-bit angle. 0 means 0 degrees, 0x100 (max value + 1) means 360 degrees'

    def from_raw_value(self, raw: bytes):
        return float((super().from_raw_value(raw) / 256) * (math.pi * 2))

    def to_raw_value(self, value) -> bytes:
        while value >= 2 * math.pi:
            value -= math.pi * 2
        while value < 0:
            value += math.pi * 2
        return super().to_raw_value(math.floor(256 * value / (math.pi * 2)))


class Nfs1Angle16(IntegerField):
    def __init__(self, **kwargs):
        kwargs['static_size'] = 2
        kwargs['byte_order'] = "little"
        kwargs['is_signed'] = True
        super().__init__(**kwargs)
        self.block_description = 'EA games 14-bit angle (little-endian), where first 2 bits unused or have unknown' \
                                 ' data. 0 means 0 degrees, 0x4000 (max value + 1) means 360 degrees'

    def from_raw_value(self, raw: bytes):
        return float(((super().from_raw_value(raw) & 0x3FFF) / 0x4000) * (math.pi * 2))

    def to_raw_value(self, value) -> bytes:
        while value >= 2 * math.pi:
            value -= math.pi * 2
        while value < 0:
            value += math.pi * 2
        return super().to_raw_value(math.floor(0x4000 * value / (math.pi * 2)))
