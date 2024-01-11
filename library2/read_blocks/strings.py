from io import BufferedReader, BytesIO
from typing import Dict

from library2.context import Context
from library2.read_blocks.basic import DataBlock


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
        }

    # For auto-generated documentation only
    @property
    def size_doc_str(self):
        if isinstance(self._length, tuple):
            (_, doc_str) = self._length
            return doc_str
        if callable(self._length):
            return "custom_func"
        return str(self._length)

    def read(self, buffer: [BufferedReader, BytesIO], ctx: Context = None, name: str = ''):
        self_len = self._length
        if isinstance(self_len, tuple):
            # cut off the documentation
            (self_len, _) = self_len
        if callable(self_len):
            self_len = self_len(ctx)
        return buffer.read(self_len).decode('utf-8')

    def write(self, data, ctx: Context = None, name: str = '') -> bytes:
        return data.encode('utf-8')
