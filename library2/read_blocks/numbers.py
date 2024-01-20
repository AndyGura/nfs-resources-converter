from io import BufferedReader, BytesIO
from typing import Dict, Literal

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
