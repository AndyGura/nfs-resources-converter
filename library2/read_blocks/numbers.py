from io import BufferedReader, BytesIO
from typing import Dict, Literal

from library2.context import Context
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

    def read(self, buffer: [BufferedReader, BytesIO], ctx: Context = None, name: str = ''):
        raw = buffer.read(self.length)
        return int.from_bytes(raw.ljust(self.length, b'\0') if self.length > 1 else raw,
                              byteorder=self.byte_order,
                              signed=self.is_signed)

    def estimate_packed_size(self, data, ctx: Context = None):
        return self.length

    def write(self, data, ctx: Context = None, name: str = '') -> bytes:
        return data.to_bytes(self.length, byteorder=self.byte_order, signed=self.is_signed).ljust(self.length, b'\0')
