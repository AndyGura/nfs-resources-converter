from abc import ABC
from io import BufferedReader, BytesIO
from math import ceil
from typing import Dict, Tuple, Any

from library.context import ReadContext, WriteContext, DocumentationContext
from library.exceptions import EndOfBufferException
from library.read_blocks.basic import DataBlock, DataBlockWithChildren
from library.read_blocks.numbers import IntegerBlock


class ArrayBlock(DataBlockWithChildren, DataBlock, ABC):

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
            try:
                return str(self._length(DocumentationContext()))
            except:
                return 'custom_func'
        return str(self._length)

    # For auto-generated documentation only
    @property
    def size_doc_str(self):
        def _multiply_docs(len_doc, size_doc):
            if len_doc == '?' or size_doc == '?':
                return '?'
            try:
                return int(len_doc) * int(size_doc)
            except ValueError:
                if len_doc == '1':
                    return size_doc
                elif size_doc == '1':
                    return len_doc
                elif (isinstance(size_doc, str) and '..' in size_doc) or (isinstance(len_doc, str) and '..' in len_doc):
                    [mnld, mxld] = len_doc.split('..') if ('..' in len_doc) else [len_doc, len_doc]
                    [mnsd, mxsd] = size_doc.split('..') if ('..' in size_doc) else [size_doc, size_doc]
                    return f'{_multiply_docs(mnld, mnsd)}..{_multiply_docs(mxld, mxsd)}'
                else:
                    if '+' in str(len_doc) or '-' in str(len_doc):
                        len_doc = f'({len_doc})'
                    if '+' in str(size_doc) or '-' in str(size_doc):
                        size_doc = f'({size_doc})'
                    return f'{len_doc}*{size_doc}'

        if self._length == 0:
            return '0'
        # when set to 0 and added some label, assume that it has some custom logic
        if isinstance(self._length, tuple) and self._length[0] == 0:
            return '?'
        child_size_doc = self.child.size_doc_str
        length_doc = self.length_doc_str
        return _multiply_docs(length_doc, child_size_doc)

    def resolve_length(self, ctx):
        self_len = self._length
        if isinstance(self_len, tuple):
            # cut off the documentation
            (self_len, _) = self_len
        if callable(self_len):
            self_len = self_len(ctx)
        return self_len

    def get_child_block(self, name: str) -> 'DataBlock':
        int(name)
        return self.child

    def get_child_block_with_data(self, unpacked_data: list, name: str) -> Tuple['DataBlock', Any]:
        return self.child, unpacked_data[int(name)]

    def new_data(self):
        if self.required_value:
            return self.required_value
        self_len = self._length
        if isinstance(self_len, tuple):
            # cut off the documentation
            (self_len, _) = self_len
        if callable(self_len):
            return []
        return [self.child.new_data()] * self_len

    def read(self, buffer: [BufferedReader, BytesIO], ctx: ReadContext = DataBlock.root_read_ctx, name: str = '',
             read_bytes_amount=None):
        res = []
        self_ctx = ReadContext(buffer=buffer, data=res, name=name, parent=ctx, read_bytes_amount=read_bytes_amount)
        self_len = self.resolve_length(ctx)
        if self.child.__class__ == IntegerBlock and self.child.length == 1 and not self.child.is_signed:
            res = list(buffer.read(self_len))
            if len(res) < self_len:
                raise EndOfBufferException(ctx=ctx)
            return res
        for i in range(self_len):
            res.append(self.child.unpack(buffer=buffer, ctx=self_ctx, name=str(i)))
        return res

    def estimate_packed_size(self, data, ctx: WriteContext = None):
        res = 0
        for item in data:
            res += self.child.estimate_packed_size(data=item, ctx=ctx)
        return res

    def offset_to_child_when_packed(self, data, child_name: str, ctx: WriteContext = None):
        index = int(child_name)
        if index >= len(data):
            raise IndexError()
        return self.estimate_packed_size(data[:index], ctx)

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        if self.child.__class__ == IntegerBlock and self.child.length == 1 and not self.child.is_signed:
            return bytes(data)
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
                'min_value': self.value_deserialize_func(0) if self.value_deserialize_func else 0,
                'max_value': self.value_deserialize_func((1 << self.bits_per_value) - 1)
                if self.value_deserialize_func
                else (1 << self.bits_per_value) - 1,
                'value_interval': self.value_deserialize_func(1) - self.value_deserialize_func(0)
                if self.value_deserialize_func
                else 1,
            }
        }

    # For auto-generated documentation only
    @property
    def length_doc_str(self):
        if isinstance(self._length, tuple):
            (_, doc_str) = self._length
            return doc_str
        if callable(self._length):
            try:
                return str(self._length(DocumentationContext()))
            except:
                return 'custom_func'
        return str(self._length)

    # For auto-generated documentation only
    @property
    def size_doc_str(self):
        length_doc = self.length_doc_str
        try:
            return str(ceil(int(length_doc) * self.bits_per_value / 8))
        except ValueError:
            return f'ceil(({length_doc})*{self.bits_per_value}/8)'

    def resolve_length(self, ctx):
        self_len = self._length
        if isinstance(self_len, tuple):
            # cut off the documentation
            (self_len, _) = self_len
        if callable(self_len):
            self_len = self_len(ctx)
        return self_len

    def get_child_block_with_data(self, unpacked_data: list, name: str) -> Tuple['DataBlock', Any]:
        return None, unpacked_data[int(name)]

    def new_data(self):
        if self.required_value:
            return self.required_value
        self_len = self._length
        if isinstance(self_len, tuple):
            # cut off the documentation
            (self_len, _) = self_len
        if callable(self_len):
            return []
        return [0] * self_len

    def read(self, buffer: [BufferedReader, BytesIO], ctx: ReadContext = DataBlock.root_read_ctx, name: str = '',
             read_bytes_amount=None):
        self_len = self.resolve_length(ctx)
        raw = buffer.read(ceil(self.bits_per_value * self_len / 8))
        bitstring = "".join([bin(x)[2:].rjust(8, "0") for x in raw])
        values = [int(bitstring[i * self.bits_per_value:(i + 1) * self.bits_per_value], 2)
                  for i in range(self_len)]
        if self.value_deserialize_func:
            values = [self.value_deserialize_func(x) for x in values]
        return values

    def estimate_packed_size(self, data, ctx: WriteContext = None):
        return ceil(self.bits_per_value * len(data) / 8)

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
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
