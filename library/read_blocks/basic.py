from abc import ABC, abstractmethod
from io import BufferedReader, BytesIO, SEEK_CUR
from typing import Dict, Any, Tuple, Literal

from library.context import ReadContext, WriteContext, DocumentationContext
from library.exceptions import DataIntegrityException, BlockDefinitionException, EndOfBufferException
from library.utils import represent_value_as_str


class DataBlock(ABC):
    root_read_ctx = ReadContext()

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

    # creates empty data
    def new_data(self):
        return self.required_value

    @abstractmethod
    def read(self, buffer: [BufferedReader, BytesIO], ctx: ReadContext = root_read_ctx, name: str = '',
             read_bytes_amount=None):
        pass

    def estimate_packed_size(self, data, ctx: WriteContext = None):
        raise BlockDefinitionException(ctx=ctx, message='Cannot estimate packed size of data block ' +
                                                        "__".join([x.__name__ for x in self.__class__.mro() if
                                                                   x.__name__ not in ["object", "ABC"]]))

    @abstractmethod
    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        pass

    def validate_after_read(self, value, ctx: ReadContext = root_read_ctx, name: str = ''):
        if self.required_value and value != self.required_value:
            raise DataIntegrityException(ctx=ctx, message=f'Expected {represent_value_as_str(self.required_value)}, '
                                                          f'found {represent_value_as_str(value)} '
                                                          f'at {name}')

    ### final method, should never override
    def unpack(self, buffer: [BufferedReader, BytesIO], ctx: ReadContext = root_read_ctx, name: str = '',
               read_bytes_amount=None):
        v = self.read(buffer=buffer, ctx=ctx, name=name, read_bytes_amount=read_bytes_amount)
        self.validate_after_read(v, ctx, name)
        return v

    ### final method, should never override
    def pack(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        return self.write(data, ctx, name)


class DataBlockWithChildren(ABC):

    ### get child block with appropriate data from this block unpacked data
    @abstractmethod
    def get_child_block_with_data(self, unpacked_data: dict, name: str) -> Tuple['DataBlock', Any]:
        pass

    ### from given unpacked data, get offset to child block by name in packed byte array
    @abstractmethod
    def offset_to_child_when_packed(self, data, child_name: str, ctx: WriteContext = None):
        index = int(child_name)
        if index >= len(data):
            raise IndexError()
        return self.estimate_packed_size(data[:index], ctx)


class BytesBlock(DataBlock):

    def __init__(self, length, allow_negative_length=False, **kwargs):
        super().__init__(**kwargs)
        self._length = length
        self.allow_negative_length = allow_negative_length

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

    def resolve_length(self, ctx):
        self_len = self._length
        if isinstance(self_len, tuple):
            # cut off the documentation
            (self_len, _) = self_len
        if callable(self_len):
            self_len = self_len(ctx)
        return self_len

    def new_data(self):
        if self.required_value:
            return self.required_value
        self_len = self._length
        if isinstance(self_len, tuple):
            # cut off the documentation
            (self_len, _) = self_len
        if callable(self_len):
            return b''
        return bytes([0] * self_len)

    def read(self, buffer: [BufferedReader, BytesIO], ctx: ReadContext = DataBlock.root_read_ctx, name: str = '',
             read_bytes_amount=None):
        self_len = self.resolve_length(ctx)
        if self_len < 0:
            if self.allow_negative_length:
                buffer.seek(self_len, SEEK_CUR)
                return b''
            raise BlockDefinitionException(ctx=ctx, message='Cannot read bytes block with negative length')
        res = buffer.read(self_len)
        if len(res) < self_len:
            raise EndOfBufferException(ctx=ctx)
        return res

    def estimate_packed_size(self, data, ctx: WriteContext = None):
        return len(data)

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        # data comes as list from GUI app
        if isinstance(data, list):
            data = bytes(data)
        return data


class SkipBlock(DataBlock):
    ### non-existing block. Can be used for optional fields

    def __init__(self, error_strategy: Literal["return_exception", "skip_silently"] = "skip_silently", **kwargs):
        super().__init__(**kwargs)
        self.error_strategy = error_strategy
        self.exception = None

    @property
    def schema(self) -> Dict:
        return {**super().schema,
                'block_description': 'Nothing, block skipped'}

    # For auto-generated documentation only
    @property
    def size_doc_str(self):
        return '0'

    def new_data(self):
        return None

    def read(self, buffer: [BufferedReader, BytesIO], ctx: ReadContext = DataBlock.root_read_ctx, name: str = '',
             read_bytes_amount=None):
        return self.exception if self.error_strategy == "return_exception" else None

    def estimate_packed_size(self, data, ctx: WriteContext = None):
        return 0

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        return bytes()
