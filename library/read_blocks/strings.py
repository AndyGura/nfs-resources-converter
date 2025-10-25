from typing import Dict

from library.context import ReadContext, WriteContext, DocumentationContext
from library.exceptions import EndOfBufferException
from library.read_blocks.basic import DataBlock


class UTF8Block(DataBlock):

    def __init__(self, length, **kwargs):
        super().__init__(**kwargs)
        self._length = length

    @property
    def schema(self) -> Dict:
        descr = 'UTF-8 string'
        if self.required_value:
            descr += f'. Always == "{self.required_value}"'
        return {
            **super().schema,
            'block_description': descr,
            'length': self.size_doc_str
        }

    # For auto-generated documentation only
    @property
    def size_doc_str(self):
        if isinstance(self._length, tuple):
            (_, doc_str) = self._length
            return doc_str
        if callable(self._length):
            try:
                return str(self._length(DocumentationContext()))
            except:
                return 'custom_func'
        return str(self._length)

    def resolve_length(self, ctx):
        self_len = self._length
        if isinstance(self_len, tuple):
            # cut off the documentation
            (self_len, _) = self_len
        if callable(self_len):
            self_len = self_len(ctx)
        return self_len

    def _get_static_length(self):
        self_len = self._length
        if isinstance(self_len, tuple):
            # cut off the documentation
            (self_len, _) = self_len
        if callable(self_len):
            return None
        return self_len

    def new_data(self):
        if self.required_value:
            return self.required_value
        return ""

    def read(self, ctx: ReadContext, name: str = '', read_bytes_amount=None):
        self_len = self.resolve_length(ctx)
        res = ctx.buffer.read(self_len).decode('utf-8')
        if len(res) < self_len:
            raise EndOfBufferException(ctx=ctx)
        if self._length == self_len:
            res = res.rstrip('\x00')
        return res

    def estimate_packed_size(self, data, ctx: WriteContext = None):
        static_length = self._get_static_length()
        if static_length is not None:
            return max(len(data), static_length)
        return len(data)

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        static_length = self._get_static_length()
        if static_length is not None and len(data) < static_length:
            data += '\x00' * (static_length - len(data))
        return data.encode('utf-8')


class NullTerminatedUTF8Block(DataBlock):

    def __init__(self, length, **kwargs):
        super().__init__(**kwargs)
        self._length = length

    @property
    def schema(self) -> Dict:
        return {**super().schema,
                'block_description': 'Null-terminated UTF-8 string. Ends with first occurrence of zero byte',
                'length': self.size_doc_str}

    # For auto-generated documentation only
    @property
    def size_doc_str(self):
        return '?'

    def read(self, ctx: ReadContext, name: str = '', read_bytes_amount=None):
        res = b''
        while True:
            nxt = ctx.buffer.read(1)
            if nxt == b'\00':
                break
            res += nxt
        return res.decode('utf-8', errors="ignore")

    def estimate_packed_size(self, data, ctx: WriteContext = None):
        return len(data) + 1

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        return data.encode('utf-8') + b'\00'
