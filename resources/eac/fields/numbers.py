from resources.basic.atomic import IntegerField


class Nfs1Float32(IntegerField):
    def __init__(self, **kwargs):
        kwargs['static_size'] = 4
        kwargs['byte_order'] = "little"
        kwargs['is_signed'] = True
        super().__init__(**kwargs)
        self.block_description = 'EA games 32-bit real number (little-endian), where last 16 bits is a fractional part'

    def from_raw_value(self, raw: bytes):
        return float(super().from_raw_value(raw) / 0x10000)

    def to_raw_value(self, value) -> bytes:
        return super().to_raw_value(round(value * 0x10000))


class Nfs1Float32_7(IntegerField):
    def __init__(self, **kwargs):
        kwargs['static_size'] = 4
        kwargs['byte_order'] = "little"
        kwargs['is_signed'] = True
        super().__init__(**kwargs)
        self.block_description = 'EA games 32-bit real number (little-endian), where last 7 bits is a fractional part'

    def from_raw_value(self, raw: bytes):
        return float(super().from_raw_value(raw) / 0x80)

    def to_raw_value(self, value) -> bytes:
        return super().to_raw_value(round(value * 0x80))


class Nfs1Float16(IntegerField):
    def __init__(self, **kwargs):
        super().__init__(static_size=2, byte_order="little", is_signed=True, **kwargs)
        self.block_description = 'EA games 16-bit real number (little-endian), where last 8 bits is a fractional part'

    def from_raw_value(self, raw: bytes):
        return float(super().from_raw_value(raw) / 0x100)

    def to_raw_value(self, value) -> bytes:
        return super().to_raw_value(round(value * 0x100))
