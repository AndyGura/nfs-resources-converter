from abc import ABC, abstractmethod
from io import BufferedReader, BytesIO
from typing import Dict, Any, Tuple, Literal, Callable, List

from library.helpers.exceptions import DataIntegrityException, BlockDefinitionException, EndOfBufferException
from library.utils import represent_value_as_str
from library2.context import ReadContext, WriteContext


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

    @abstractmethod
    def read(self, buffer: [BufferedReader, BytesIO], ctx: ReadContext = None, name: str = '', read_bytes_amount=None):
        pass

    def estimate_packed_size(self, data, ctx: WriteContext = None):
        raise BlockDefinitionException('Cannot estimate packed size of data block ' +
                                       "__".join([x.__name__ for x in self.__class__.mro() if
                                                  x.__name__ not in ["object", "ABC"]]))

    @abstractmethod
    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        pass

    def validate_after_read(self, value, ctx: ReadContext = None, name: str = ''):
        if self.required_value and value != self.required_value:
            raise DataIntegrityException(f'Expected {represent_value_as_str(self.required_value)}, '
                                         f'found {represent_value_as_str(value)}')

    ### final method, should never override
    def unpack(self, buffer: [BufferedReader, BytesIO], ctx: ReadContext = None, name: str = '',
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

    def read(self, buffer: [BufferedReader, BytesIO], ctx: ReadContext = None, name: str = '', read_bytes_amount=None):
        self_len = self._length
        if isinstance(self_len, tuple):
            # cut off the documentation
            (self_len, _) = self_len
        if callable(self_len):
            self_len = self_len(ctx)
        res = buffer.read(self_len)
        if len(res) < self_len:
            raise EndOfBufferException()
        return res

    def estimate_packed_size(self, data, ctx: WriteContext = None):
        return len(data)

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
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

    def read(self, buffer: [BufferedReader, BytesIO], ctx: ReadContext = None, name: str = '', read_bytes_amount=None):
        return self.exception if self.error_strategy == "return_exception" else None

    def estimate_packed_size(self, data, ctx: WriteContext = None):
        return 0

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        return bytes()


class HeapBlock(BytesBlock):
    ### a heap, containing one or more blocks somewhere in it

    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Heap',
            'child_schema': self.child.schema,
        }

    def estimate_packed_size(self, data, ctx: WriteContext = None):
        packed_sizes = {name: self.child.estimate_packed_size(data) for (name, data) in data.items()}
        last_item_name, last_offset = max(self.layout_children([x for x in packed_sizes.items()]), key=lambda d: d[1])
        return last_offset + packed_sizes[last_item_name]

    # for each item provide tuple with name and length
    def default_layout(self, items: List[Tuple[str, int]]):
        offset = 0
        res = []
        for (name, packed_data_size) in items:
            res.append((name, offset))
            offset += packed_data_size
        return res

    def __init__(self, child: DataBlock, children_descr: Callable, layout_children: Callable = None, **kwargs):
        super().__init__(**kwargs)
        self.child = child
        self.children_descr = children_descr
        self.layout_children = layout_children
        if not self.layout_children:
            self.layout_children = self.default_layout

    def get_child_block_with_data(self, unpacked_data, name: str) -> Tuple['DataBlock', Any]:
        return self.child, unpacked_data.get(name)

    def read(self, buffer: [BufferedReader, BytesIO], ctx: ReadContext = None, name: str = '', read_bytes_amount=None):
        children = self.children_descr(ctx)
        bts = super().read(buffer, ctx, name, read_bytes_amount)
        res = {}
        self_ctx = ReadContext(buffer=buffer, data=res, name=name, block=self, parent=ctx,
                               read_bytes_amount=read_bytes_amount)
        for (name, offset, length) in children:
            self_ctx.buffer = BytesIO(bts[offset:offset + length] if length is not None else bts[offset:])
            res[name] = self.child.unpack(self_ctx.buffer, ctx=self_ctx, name=name, read_bytes_amount=length)
        return res

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        packed_items = {name: self.child.pack(data) for (name, data) in data.items()}
        res = b''
        for (name, offset) in sorted(self.layout_children([(name, len(bts)) for name, bts in packed_items.items()]),
                                     key=lambda d: d[1]):
            if len(res) < offset:
                res += bytes([0] * (offset - offset.size()))
            elif len(res) > offset:
                # TODO support
                raise NotImplementedError('Intersecting blocks in heap not supported')
            res += packed_items[name]
        return res
