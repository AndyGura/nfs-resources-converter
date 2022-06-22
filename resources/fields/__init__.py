from abc import ABC, abstractmethod, abstractclassmethod
from math import floor
from typing import Literal

from buffer_utils import read_byte


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

    @abstractmethod
    def read(self, buffer, size):
        if self.min_size > size:
            raise Exception(f'Cannot read block {self.__class__.__name__}: minimum block size {self.min_size}, available size: {size}')

    @abstractmethod
    def write(self, buffer, value):
        pass


class ResourceField(ReadBlock, ABC):
    is_unknown = False

    def __init__(self, description: str = '', is_unknown: bool = False):
        self.description = description
        self.is_unknown = is_unknown


class ByteField(ResourceField):
    block_description = '1-byte field'

    @property
    def size(self):
        return 1

    def read(self, buffer, size):
        super().read(buffer, size)
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

    def read(self, buffer, size):
        super().read(buffer, size)
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

    def read(self, buffer, size):
        value = super().read(buffer, size)
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

    def read(self, buffer, size):
        super().read(buffer, size)
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
