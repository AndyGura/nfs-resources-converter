from io import BufferedReader, BytesIO
from typing import Dict, Literal, List, Tuple

from library.helpers.exceptions import EndOfBufferException
from library2.context import ReadContext, WriteContext
from library2.read_blocks.basic import DataBlock


class IntegerBlock(DataBlock):

    def __init__(self, length, is_signed: bool = False, byte_order: Literal["little", "big"] = "little", **kwargs):
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
        if self.required_value is not None:
            descr += f'. Always == {hex(self.required_value)}'
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

    def read(self, buffer: [BufferedReader, BytesIO], ctx: ReadContext = None, name: str = '', read_bytes_amount=None):
        raw = buffer.read(self.length)
        if len(raw) < self.length:
            raise EndOfBufferException()
        return int.from_bytes(raw, byteorder=self.byte_order, signed=self.is_signed)

    def estimate_packed_size(self, data, ctx: WriteContext = None):
        return self.length

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        return data.to_bytes(self.length, byteorder=self.byte_order, signed=self.is_signed).ljust(self.length, b'\0')


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

    def read(self, buffer: [BufferedReader, BytesIO], ctx: ReadContext = None, name: str = '', read_bytes_amount=None):
        value = super().read(buffer, ctx, name, read_bytes_amount)
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
                'block_description': 'Enum of 256 possible values<br/><details><summary>Value names:</summary>'
                                     + '<br/>'.join([f'{i}: {x}'
                                                     for i, x in enumerate(self.enum_name_map)
                                                     if x != str(i)]) + '</details>'}

    def __init__(self, enum_names: List[Tuple[int, str]], **kwargs):
        super().__init__(length=1, **kwargs)
        self.enum_names = enum_names
        self.enum_name_map = [str(i) for i in range(256)]
        for value, name in self.enum_names:
            self.enum_name_map[value] = name

    def read(self, buffer: [BufferedReader, BytesIO], ctx: ReadContext = None, name: str = '', read_bytes_amount=None):
        return self.enum_name_map[super().read(buffer, ctx, name, read_bytes_amount)]

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        return super().write(self.enum_name_map.index(data), ctx, name)
