from abc import ABC, abstractmethod
from functools import cached_property
from inspect import getsourcelines
from io import BufferedReader, BytesIO
from math import floor
from typing import Literal, final

from buffer_utils import read_byte, write_byte, read_3int, write_3int, read_short, write_short


class ReadBlock(ABC):
    block_description = None
    description = None

    @property
    @abstractmethod
    def size(self):
        pass

    @property
    def min_size(self):
        return self.size

    @property
    def max_size(self):
        return self.size

    def read(self, buffer: [BufferedReader, BytesIO], size: int):
        if self.min_size > size:
            raise Exception(f'Cannot read {self.__class__.__name__}: min size {self.min_size}, available: {size}')
        return self._read_internal(buffer, size)

    @abstractmethod
    def _read_internal(self, buffer: [BufferedReader, BytesIO], size: int):
        pass

    def write(self, buffer, data):
        self._write_internal(buffer, data)

    @abstractmethod
    def _write_internal(self, buffer, value):
        pass


class ResourceField(ReadBlock, ABC):
    is_unknown = False

    def __init__(self, description: str = '', is_unknown: bool = False):
        super().__init__()
        self.description = description
        self.is_unknown = is_unknown
        if not self.description and self.is_unknown:
            self.description = 'Unknown purpose'

    @final
    def read(self, buffer: [BufferedReader, BytesIO], size: int):
        return super().read(buffer, size)

    @final
    def write(self, buffer, data):
        super().write(buffer, data)


class ByteField(ResourceField):
    block_description = '1-byte unsigned integer'

    @property
    def size(self):
        return 1

    def _read_internal(self, buffer, size):
        return read_byte(buffer)

    def _write_internal(self, buffer, value):
        write_byte(buffer, value)


class Int2Field(ResourceField):
    block_description = '2-byte unsigned integer'

    @property
    def size(self):
        return 2

    def _read_internal(self, buffer, size):
        return read_short(buffer)

    def _write_internal(self, buffer, value):
        write_short(buffer, value)


class Int3Field(ResourceField):
    block_description = '3-byte unsigned integer'

    @property
    def size(self):
        return 3

    def _read_internal(self, buffer, size):
        return read_3int(buffer)

    def _write_internal(self, buffer, value):
        write_3int(buffer, value)


class BitmapField(ResourceField):
    block_description = '1-byte field, set of 8 flags'
    masks = [pow(2, 7 - i) for i in range(8)]

    @property
    def size(self):
        return 1

    def __init__(self, *args, flag_names: list[str] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.flag_names = flag_names

    def _read_internal(self, buffer, size):
        value = read_byte(buffer)
        return {(self.flag_names[i] if self.flag_names else str(i)): bool(value & mask) for (i, mask) in
                enumerate(self.masks)}

    def _write_internal(self, buffer, value):
        raise NotImplementedError


class RequiredByteField(ByteField):

    @property
    def size(self):
        return 1

    def __init__(self, *args, required_value: int, **kwargs):
        super().__init__(*args, **kwargs)
        self.required_value = required_value
        self.block_description = f'Always == {hex(self.required_value)}'

    def _read_internal(self, buffer, size):
        value = super()._read_internal(buffer, size)
        if value != self.required_value:
            raise Exception(f'Expected {hex(self.required_value)}, found {hex(value)}')
        return value


class ArrayField(ResourceField):
    child = None

    @cached_property
    def size(self):
        return self.child.size * self.length

    @cached_property
    def min_size(self):
        if callable(self.length):
            return 0
        return self.child.min_size * self.length if self.length_strategy == "strict" else 0

    @cached_property
    def max_size(self):
        if callable(self.length):
            return float('inf')
        return self.child.max_size * self.length

    def __init__(self, *args, child: ResourceField, length: Literal[int, callable] = None,
                 length_strategy: Literal["strict", "read_available"] = "strict", **kwargs):
        super().__init__(*args, **kwargs)
        self.child = child
        self.length = length
        self.length_strategy = length_strategy
        if callable(self.length):
            length_label = f"<{getsourcelines(self.length)[0][0].split('lambda self:')[-1].split(',')[0].strip().replace('self.', '')}>"
        elif self.length_strategy == "read_available":
            length_label = f'0..{self.length}'
        else:
            length_label = str(self.length)
        self.block_description = f'Array of {length_label} items'

    def _read_internal(self, buffer, size):
        res = []
        amount = self.length
        if self.length_strategy == "read_available":
            amount = min(amount, floor(size / self.child.size))
        for _ in range(amount):
            res.append(self.child.read(buffer, size))
            size -= self.child.size
        return res

    def _write_internal(self, buffer, value):
        for item in value:
            self.child.write(buffer, item)


from .colors import (Color24BitDosField,
                     Color24BitField,
                     Color32BitField,
                     Color16Bit0565Field,
                     )
