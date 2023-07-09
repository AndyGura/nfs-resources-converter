from io import BufferedReader, BytesIO
from math import floor, ceil
from typing import Literal

from library.helpers.exceptions import BlockDefinitionException
from library.read_blocks.data_block import DataBlock
from library.read_data import ReadData


class SubByteArrayBlock(DataBlock):

    def get_size(self, state):
        length = self.length
        if length is None:
            length = state.get('length')
        if length is None:
            return None
        return ceil(self.bits_per_value * length / 8)

    def get_min_size(self, state):
        if self.length is None and state.get('length') is None:
            return 0
        return self.get_size(state) if self.length_strategy == "strict" else 0

    def get_max_size(self, state):
        if self.length is None and state.get('length') is None:
            return float('inf')
        return self.get_size(state)

    def __init__(self,
                 bits_per_value: int,
                 length: int = None,
                 length_strategy: Literal["strict", "read_available"] = "strict",
                 length_label: str = None,
                 children_simplified: bool = False,
                 value_deserialize_func: callable = lambda x: x,
                 value_serialize_func: callable = lambda x: x,
                 **kwargs):
        super().__init__(**kwargs)
        self.bits_per_value = bits_per_value
        self.length = length
        self.length_strategy = length_strategy
        self.children_simplified = children_simplified
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

    def _load_value(self, buffer: [BufferedReader, BytesIO], size: int, state):
        length = self.length or state.get('length')
        if length is None and self.length_strategy != "read_available":
            raise BlockDefinitionException('Sub-byte array field length is unknown')
        if self.length_strategy == "read_available":
            raise NotImplementedError('Read available ot implemented for sub-byte array :(')
        return super(SubByteArrayBlock, self)._load_value(buffer, size, state)

    def from_raw_value(self, raw: bytes, state: dict):
        bitstring = "".join([bin(x)[2:].rjust(8, "0") for x in raw])
        values = [int(bitstring[i * self.bits_per_value:(i + 1) * self.bits_per_value], 2)
                  for i in range(floor(len(bitstring) / self.bits_per_value))]
        if self.children_simplified:
            return [self.value_deserialize_func(x) for x in values]
        else:
            return [ReadData(value=self.value_deserialize_func(x), block=None, block_state=state) for x in values]

    def to_raw_value(self, data: ReadData) -> bytes:
        bitstring = "".join(
            bin(self.value_serialize_func(item))[2:].rjust(self.bits_per_value, "0") for item in data.value)
        padding = len(bitstring) % 8
        if padding != 0:
            bitstring += '0' * (8 - padding)
        byte_array = bytearray()
        for i in range(0, len(bitstring), 8):
            byte = int(bitstring[i:i + 8], 2)
            byte_array.append(byte)
        return bytes(byte_array)
