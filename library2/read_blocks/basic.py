from abc import ABC, abstractmethod
from io import BufferedReader, BytesIO
from typing import Dict, Any, Tuple

from library.helpers.exceptions import DataIntegrityException, BlockDefinitionException
from library.utils import represent_value_as_str
from library2.context import Context


class DataBlock(ABC):

    def __init__(self, required_value=None, **kwargs):
        self.required_value = required_value

    # For auto-generated documentation only
    @property
    def size_doc_str(self):
        return '?'

    # For GUI
    @property
    def schema(self) -> Dict:
        s = {
            'block_class_mro': '__'.join(
                [x.__name__ for x in self.__class__.mro() if x.__name__ not in ['object', 'ABC']]),
            'block_description': '',
            'serializable_to_disc': False,
        }
        if self.required_value:
            s['required_value'] = self.required_value
        return s

    def get_child_block(self, unpacked_data: Any, name: str) -> Tuple['DataBlock', Any]:
        raise BlockDefinitionException('Data block ' +
                                       "__".join([x.__name__ for x in self.__class__.mro() if
                                                  x.__name__ not in ["object", "ABC"]]) +
                                       ' cannot contain children blocks')

    @abstractmethod
    def read(self, buffer: [BufferedReader, BytesIO], ctx: Context = None, name: str = ''):
        pass

    @abstractmethod
    def write(self, data, ctx: Context = None, name: str = '') -> bytes:
        pass

    def validate_after_read(self, value, ctx: Context = None, name: str = ''):
        if self.required_value and value != self.required_value:
            raise DataIntegrityException(f'Expected {represent_value_as_str(self.required_value)}, '
                                         f'found {represent_value_as_str(value)}')

    ### final method, should never override
    def unpack(self, buffer: [BufferedReader, BytesIO], ctx: Context = None, name: str = ''):
        v = self.read(buffer, ctx, name)
        self.validate_after_read(v, ctx, name)
        return v

    ### final method, should never override
    def pack(self, data, ctx: Context = None, name: str = '') -> bytes:
        return self.write(data, ctx, name)


class BytesBlock(DataBlock):

    def __init__(self, length, **kwargs):
        super().__init__(**kwargs)
        self._length = length

    # For auto-generated documentation only
    @property
    def size_doc_str(self):
        if isinstance(self._length, tuple):
            (_, doc_str) = self._length
            return doc_str
        if callable(self._length):
            return "custom_func"
        else:
            return str(self._length)

    @property
    def schema(self) -> Dict:
        descr = 'Bytes'
        if self.required_value is not None:
            descr += f'. Always == {str(self.required_value)}'
        return {
            **super().schema,
            'block_description': descr,
        }

    def read(self, buffer: [BufferedReader, BytesIO], ctx: Context = None, name: str = ''):
        self_len = self._length
        if isinstance(self_len, tuple):
            # cut off the documentation
            (self_len, _) = self_len
        if callable(self_len):
            self_len = self_len(ctx)
        return buffer.read(self_len)

    def write(self, data, ctx: Context = None, name: str = '') -> bytes:
        return data
