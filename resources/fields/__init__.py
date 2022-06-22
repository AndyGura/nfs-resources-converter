from abc import ABC, abstractmethod
from io import BufferedReader, BytesIO
from math import floor
from typing import Literal, final

from buffer_utils import read_byte


class ReadBlock(ABC):
    block_description = None
    description = None
    allow_multiread = False

    def __init__(self) -> None:
        super().__init__()
        self._data = None

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

    @property
    def data(self):
        if self._data is None:
            raise Exception("Block wasn't read yet")
        return self._data

    @final
    def read(self, buffer: [BufferedReader, BytesIO], size: int):
        if self._data is not None and not self.allow_multiread:
            raise Exception('Block was already read')
        if self.min_size > size:
            raise Exception(f'Cannot read block {self.__class__.__name__}: minimum block size {self.min_size}, available size: {size}')
        self._data = self._read_internal(buffer, size)
        return self._data

    @abstractmethod
    def _read_internal(self, buffer: [BufferedReader, BytesIO], size: int):
        pass

    @abstractmethod
    def write(self, buffer, value):
        pass


class ResourceField(ReadBlock, ABC):
    is_unknown = False
    allow_multiread = True

    def __init__(self, description: str = '', is_unknown: bool = False):
        super().__init__()
        self.description = description
        self.is_unknown = is_unknown


class ByteField(ResourceField):
    block_description = '1-byte field'

    @property
    def size(self):
        return 1

    def _read_internal(self, buffer, size):
        return read_byte(buffer)

    def write(self, buffer, value):
        raise NotImplementedError


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
        return {(self.flag_names[i] if self.flag_names else str(i)): bool(value & mask) for (i, mask) in enumerate(self.masks)}

    def write(self, buffer, value):
        raise NotImplementedError


class RequiredByteField(ByteField):
    block_description = '1-byte field'

    @property
    def size(self):
        return 1

    def __init__(self, *args, required_value: int, **kwargs):
        super().__init__(*args, **kwargs)
        self.required_value = required_value
        self.block_description += f' (required value: {hex(self.required_value)})'

    def _read_internal(self, buffer, size):
        value = super()._read_internal(buffer, size)
        if value != self.required_value:
            raise Exception(f'Expected {hex(self.required_value)}, found {hex(value)}')
        return value

    def write(self, buffer, value):
        raise NotImplementedError


class ArrayField(ResourceField):
    block_description = 'Array field'
    child = None

    @property
    def size(self):
        return self.child.size * self.length

    @property
    def min_size(self):
        return self.child.min_size * self.length if self.length_strategy == "strict" else 0

    @property
    def max_size(self):
        return self.child.max_size * self.length

    def __init__(self, *args, child: ResourceField, length: int, length_strategy: Literal["strict", "read_available"]="strict", **kwargs):
        super().__init__(*args, **kwargs)
        self.child = child
        self.length = length
        self.length_strategy = length_strategy
        self.block_description += f' (size: {length} bytes)'

    def _read_internal(self, buffer, size):
        res = []
        amount = self.length
        if self.length_strategy == "read_available":
            amount = min(amount, floor(size / self.child.size))
        for _ in range(amount):
            res.append(self.child.read(buffer, size))
            size -= self.child.size
        return res

    def write(self, buffer, value):
        raise NotImplementedError


from .colors import (Color24BitDosField,
                     Color24BitField,
                     Color32BitField,
                     Color16BitField,
                     )
