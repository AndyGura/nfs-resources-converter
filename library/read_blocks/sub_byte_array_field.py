from io import BufferedReader, BytesIO
from math import floor, ceil
from typing import Literal

from library.read_blocks.exceptions import BlockDefinitionException
from library.read_blocks.read_block import ReadBlock


class SubByteArrayBlock(ReadBlock):

    @property
    def size(self):
        if self.length is None:
            return None
        return ceil(self.bits_per_value * self.length / 8)

    @property
    def min_size(self):
        if self.length is None:
            return 0
        return self.size if self.length_strategy == "strict" else 0

    @property
    def max_size(self):
        if self.length is None:
            return float('inf')
        return self.size

    def __init__(self,
                 bits_per_value: int,
                 length: int = None,
                 length_strategy: Literal["strict", "read_available"] = "strict",
                 length_label: str = None,
                 value_deserialize_func: callable = lambda x: x,
                 value_serialize_func: callable = lambda x: x,
                 **kwargs):
        super().__init__(bits_per_value=bits_per_value,
                         length=length,
                         length_strategy=length_strategy,
                         length_label=length_label,
                         value_deserialize_func=value_deserialize_func,
                         value_serialize_func=value_serialize_func,
                         **kwargs)
        self.bits_per_value = bits_per_value
        self.length = length
        self.length_strategy = length_strategy
        self.value_deserialize_func = value_deserialize_func
        self.value_serialize_func = value_serialize_func
        if length_label is None:
            if self.length is None:
                length_label = '?'
            elif self.length_strategy == "read_available":
                length_label = f'0..{self.length}'
            else:
                length_label = str(self.length)
        self.length_label = length_label
        self.block_description = f'Array of {length_label} sub-byte numbers. Each number consists of {bits_per_value} bits'

    def load_value(self, buffer: [BufferedReader, BytesIO], size: int, parent_read_data: dict = None):
        if self.length is None and self.length_strategy != "read_available":
            raise BlockDefinitionException('Sub-byte array field length is unknown')
        if self.length_strategy == "read_available":
            raise NotImplementedError('Read available ot implemented for sub-byte array :(')
        return super(SubByteArrayBlock, self).load_value(buffer, size, parent_read_data)

    def from_raw_value(self, raw: bytes):
        bitstring = "".join([bin(x)[2:].rjust(8, "0") for x in raw])
        values = [int(bitstring[i * self.bits_per_value:(i + 1) * self.bits_per_value], 2)
                  for i in range(floor(len(bitstring) / self.bits_per_value))]
        return [self.value_deserialize_func(x) for x in values]

    def to_raw_value(self, value) -> bytes:
        pass
