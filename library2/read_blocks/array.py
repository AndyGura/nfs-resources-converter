from abc import ABC
from io import BufferedReader, BytesIO
from math import ceil
from typing import Dict, Tuple, Any

from library2.context import Context
from library2.read_blocks.basic import DataBlock


class ArrayBlock(DataBlock, ABC):

    def __init__(self, child: DataBlock, length, **kwargs):
        super().__init__(**kwargs)
        self.child = child
        self._length = length

    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': f'Array of `{self.length_doc_str}` items',
            'child_schema': self.child.schema
        }

    # For auto-generated documentation only
    @property
    def length_doc_str(self):
        if isinstance(self._length, tuple):
            (_, doc_str) = self._length
            return doc_str
        if callable(self._length):
            return "custom_func"
        return str(self._length)

    # For auto-generated documentation only
    @property
    def size_doc_str(self):
        child_size_doc = self.child.size_doc_str
        if child_size_doc == '?':
            return '?'
        length_doc = self.length_doc_str
        try:
            return int(length_doc) * int(child_size_doc)
        except ValueError:
            return f'{length_doc}*{child_size_doc}'

    def get_child_block(self, unpacked_data: list, name: str) -> Tuple['DataBlock', Any]:
        return self.child, unpacked_data[int(name)]

    def read(self, buffer: [BufferedReader, BytesIO], ctx: Context = None, name: str = ''):
        res = []
        self_ctx = Context(buffer=buffer, data=res, name=name, parent=ctx)
        self_len = self._length
        if isinstance(self_len, tuple):
            # cut off the documentation
            (self_len, _) = self_len
        if callable(self_len):
            self_len = self_len(ctx)
        for i in range(self_len):
            res.append(self.child.unpack(buffer=buffer, ctx=self_ctx, name=str(i)))
        return res

    def write(self, data, ctx: Context = None, name: str = '') -> bytes:
        res = bytes()
        for i, item in enumerate(data):
            res += self.child.pack(data=item, ctx=ctx, name=str(i))
        return res


class SubByteArrayBlock(DataBlock):

    def __init__(self,
                 length,
                 bits_per_value: int,
                 value_deserialize_func: callable = None,
                 value_serialize_func: callable = None,
                 **kwargs):
        super().__init__(**kwargs)
        self._length = length
        self.bits_per_value = bits_per_value
        self.value_deserialize_func = value_deserialize_func
        self.value_serialize_func = value_serialize_func

    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': f'Array of `{self.length_doc_str}` sub-byte numbers. Each number consists of {self.bits_per_value} bits',
            'child_schema': {
                'block_class_mro': 'IntegerBlock__DataBlock',
                'min_value': self.value_deserialize_func(0),
                'max_value': self.value_deserialize_func((1 << self.bits_per_value) - 1),
                'value_interval': self.value_deserialize_func(1) - self.value_deserialize_func(0),
            }
        }

    # For auto-generated documentation only
    @property
    def length_doc_str(self):
        if isinstance(self._length, tuple):
            (_, doc_str) = self._length
            return doc_str
        if callable(self._length):
            return "custom_func"
        return str(self._length)

    # For auto-generated documentation only
    @property
    def size_doc_str(self):
        length_doc = self.length_doc_str
        try:
            return str(ceil(int(length_doc) * self.bits_per_value / 8))
        except ValueError:
            return f'ceil(({length_doc})*{self.bits_per_value}/8)'

    def get_child_block(self, unpacked_data: list, name: str) -> Tuple['DataBlock', Any]:
        return None, unpacked_data[int(name)]

    def read(self, buffer: [BufferedReader, BytesIO], ctx: Context = None, name: str = ''):
        self_len = self._length
        if isinstance(self_len, tuple):
            # cut off the documentation
            (self_len, _) = self_len
        if callable(self_len):
            self_len = self_len(ctx)
        raw = buffer.read(ceil(self.bits_per_value * self_len / 8))
        bitstring = "".join([bin(x)[2:].rjust(8, "0") for x in raw])
        values = [int(bitstring[i * self.bits_per_value:(i + 1) * self.bits_per_value], 2)
                  for i in range(self_len)]
        if self.value_deserialize_func:
            values = [self.value_deserialize_func(x) for x in values]
        return values

    def write(self, data, ctx: Context = None, name: str = '') -> bytes:
        value_serialize_func = self.value_serialize_func if self.value_serialize_func else lambda x: x
        bitstring = "".join(bin(value_serialize_func(item))[2:].rjust(self.bits_per_value, "0") for item in data)
        padding = len(bitstring) % 8
        if padding != 0:
            bitstring += '0' * (8 - padding)
        byte_array = bytearray()
        for i in range(0, len(bitstring), 8):
            byte = int(bitstring[i:i + 8], 2)
            byte_array.append(byte)
        return bytes(byte_array)
