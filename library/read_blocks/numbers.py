import struct
from typing import Dict, Literal, List, Tuple

from library.context import ReadContext, WriteContext
from library.exceptions import EndOfBufferException, DataIntegrityException
from library.read_blocks.basic import DataBlock


class IntegerBlock(DataBlock):

    def __init__(self, length: int, is_signed: bool = False, byte_order: Literal["little", "big"] = "little", **kwargs):
        super().__init__(**kwargs)
        self.length = length
        self.is_signed = is_signed
        self.byte_order = byte_order

    @property
    def schema(self) -> Dict:
        descr = f'{self.length}-byte{"s" if self.length > 1 else ""} ' \
                f'{"un" if not self.is_signed else ""}signed integer'
        if self.length > 1:
            descr += f' ({self.byte_order} endian)'
        if self.value_validator is not None:
            descr += f'. {self.value_validator}'
        return {
            **super().schema,
            'block_description': descr,
            'min_value': -(1 << (self.length * 8 - 1)) if self.is_signed else 0,
            'max_value': ((1 << (self.length * 8 - 1)) if self.is_signed else (1 << (self.length * 8))) - 1,
            'value_interval': 1,
        }

    # For auto-generated documentation only
    @property
    def size_doc_str(self):
        return str(self.length)

    def new_data(self):
        if self.value_validator:
            return self.value_validator.new_data()
        return 0

    def read(self, ctx: ReadContext, name: str = '', read_bytes_amount=None):
        raw = ctx.buffer.read(self.length)
        if len(raw) < self.length:
            raise EndOfBufferException(ctx=ctx)
        return int.from_bytes(raw, byteorder=self.byte_order, signed=self.is_signed)

    def estimate_packed_size(self, data, ctx: WriteContext = None):
        return self.length

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        return data.to_bytes(self.length, byteorder=self.byte_order, signed=self.is_signed).ljust(self.length, b'\0')


class FixedPointBlock(IntegerBlock):
    @property
    def schema(self) -> Dict:
        super_schema = super().schema
        descr = (f'{self.length * 8}-bit real number ({self.byte_order}-endian, '
                 f'{"" if self.is_signed else "not "}signed), where last {self.fraction_bits} '
                 f'bits is a fractional part')
        if self.value_validator is not None:
            descr += f'. {self.value_validator}'
        return {
            **super_schema,
            'min_value': float(super_schema['min_value'] / (1 << self.fraction_bits)),
            'max_value': float(super_schema['max_value'] / (1 << self.fraction_bits)),
            'value_interval': float(super_schema['value_interval'] / (1 << self.fraction_bits)),
            'block_description': descr,
        }

    def __init__(self, fraction_bits: int, **kwargs):
        super().__init__(**kwargs)
        self.fraction_bits = fraction_bits

    def read(self, ctx: ReadContext, name: str = '', read_bytes_amount=None):
        return float(super().read(ctx, name, read_bytes_amount) / (1 << self.fraction_bits))

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        data = max(min(round(data * (1 << self.fraction_bits)),
                       ((1 << (self.length * 8 - 1)) if self.is_signed else (1 << (self.length * 8))) - 1),
                   -(1 << (self.length * 8 - 1)) if self.is_signed else 0)
        return super().write(data, ctx, name)


class DecimalBlock(DataBlock):

    def __init__(self, length: int, byte_order: Literal["little", "big"] = "little", **kwargs):
        super().__init__(**kwargs)
        if length not in [4, 8]:
            raise Exception('DecimalsBlock supports only 4 or 8 bytes length')
        self.length = length
        self.byte_order = byte_order

    @property
    def schema(self) -> Dict:
        descr = f'{"Float" if self.length == 4 else "Double"} number ({self.byte_order}-endian)'
        if self.value_validator is not None:
            descr += f'. {self.value_validator}'
        return {
            **super().schema,
            'block_description': descr,
        }

    @property
    def size_doc_str(self):
        return str(self.length)

    def new_data(self):
        return 0.0

    def read(self, ctx: ReadContext, name: str = '', read_bytes_amount=None):
        raw = ctx.buffer.read(self.length)
        if len(raw) < self.length:
            raise EndOfBufferException(ctx=ctx)
        f = 'f' if self.length == 4 else 'd'
        return struct.unpack(f'<{f}' if self.byte_order == 'little' else f'>{f}', raw)[0]

    def estimate_packed_size(self, data, ctx: WriteContext = None):
        return self.length

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        f = 'f' if self.length == 4 else 'd'
        return struct.pack(f'<{f}' if self.byte_order == 'little' else f'>{f}', data)


class BitFlagsBlock(IntegerBlock):

    @property
    def schema(self) -> Dict:
        return {**super().schema,
                'block_description': '8 flags container<br/><details><summary>flag names (from least to most significant)</summary>'
                                     + '<br/>'.join(
                    [f'{i}: {x}' for i, x in enumerate(self.flag_name_map) if x != str(i)]) + '</details>'}

    def __init__(self, flag_names: List[Tuple[int, str]], **kwargs):
        super().__init__(length=1, is_signed=False, **kwargs)
        self.flag_names = flag_names
        self.flag_name_map = [str(i) for i in range(8)]
        for value, name in self.flag_names:
            self.flag_name_map[value] = name

    def new_data(self):
        return [False] * 8

    def read(self, ctx: ReadContext, name: str = '', read_bytes_amount=None):
        value = super().read(ctx, name, read_bytes_amount)
        res = {}
        for i in range(8):
            res[self.flag_name_map[i]] = bool(value & (1 if i == 0 else 1 << i))
        return res

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        res = 0
        for i in range(8):
            if data[self.flag_name_map[i]]:
                res = res | (1 << i)
        return super().write(res, ctx, name)


class EnumByteBlock(IntegerBlock):

    @property
    def schema(self) -> Dict:
        return {**super().schema,
                'enum_names': self.enum_names,
                'block_description': 'Enum of 256 possible values<br/><details><summary>Value names:</summary>'
                                     + '<br/>'.join([f'{i}: {x}'
                                                     for i, x in enumerate(self.enum_name_map)
                                                     if x != str(i)]) + '</details>'}

    def __init__(self, enum_names: List[Tuple[int, str]], raise_error_on_unknown=False, **kwargs):
        super().__init__(length=1, **kwargs)
        self.enum_names = enum_names
        self.raise_error_on_unknown = raise_error_on_unknown
        self.enum_name_map = [str(i) if not self.raise_error_on_unknown else None for i in range(256)]
        for value, name in self.enum_names:
            self.enum_name_map[value] = name

    def new_data(self):
        if self.value_validator:
            return self.value_validator.new_data()
        return next(x for x in self.enum_name_map if x is not None)

    def read(self, ctx: ReadContext, name: str = '', read_bytes_amount=None):
        raw = super().read(ctx, name, read_bytes_amount)
        if self.raise_error_on_unknown and self.enum_name_map[raw] is None:
            raise DataIntegrityException(ctx=ctx, message=f'Unknown enum value {raw} at {name}')
        return self.enum_name_map[raw]

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        return super().write(self.enum_name_map.index(data), ctx, name)
