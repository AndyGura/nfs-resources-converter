from abc import ABC, abstractmethod
from io import BufferedReader, BytesIO
from math import floor
from typing import Literal, final

from buffer_utils import read_byte, write_byte, read_3int, write_3int, read_short, write_short
from exceptions import EndOfBufferException, BlockIntegrityException, BlockDefinitionException


class ReadBlock(ABC):
    block_description = None
    description = None

    def __init__(self, **kwargs):
        self.instantiate_kwargs = kwargs

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

    def read(self, buffer: [BufferedReader, BytesIO], size: int, parent_read_data: dict = None):
        if self.min_size > size:
            raise EndOfBufferException(f'Cannot read {self.__class__.__name__}: '
                                       f'min size {self.min_size}, available: {size}')
        return self._read_internal(buffer, size, parent_read_data)

    @abstractmethod
    def _read_internal(self, buffer: [BufferedReader, BytesIO], size: int, parent_read_data: dict = None):
        pass

    def write(self, buffer, data):
        self._write_internal(buffer, data)

    @abstractmethod
    def _write_internal(self, buffer, value):
        pass


class ResourceField(ReadBlock, ABC):
    is_unknown = False

    def __init__(self, description: str = '', is_unknown: bool = False, **kwargs):
        super().__init__(description=description,
                         is_unknown=is_unknown,
                         **kwargs)
        self.description = description
        self.is_unknown = is_unknown
        if not self.description and self.is_unknown:
            self.description = 'Unknown purpose'

    @final
    def read(self, buffer: [BufferedReader, BytesIO], size: int, parent_read_data: dict = None):
        return super().read(buffer, size, parent_read_data)

    @final
    def read_multiple(self, buffer: [BufferedReader, BytesIO], size: int, length: int, parent_read_data: dict = None):
        if self.min_size * length > size:
            raise EndOfBufferException(f'Cannot read multiple {self.__class__.__name__}: '
                                       f'min size {self.min_size * length}, available: {size}')
        return self._read_multiple_internal(buffer, size, length, parent_read_data)

    def _read_multiple_internal(self, buffer: [BufferedReader, BytesIO], size: int, length: int, parent_read_data: dict = None):
        raise NotImplementedError()

    @final
    def write(self, buffer, data):
        super().write(buffer, data)


class ByteField(ResourceField):
    block_description = '1-byte unsigned integer'

    @property
    def size(self):
        return 1

    def _read_internal(self, buffer, size, parent_read_data: dict = None):
        return read_byte(buffer)

    def _read_multiple_internal(self, buffer: [BufferedReader, BytesIO], size: int, length: int, parent_read_data: dict = None):
        return list(buffer.read(length))

    def _write_internal(self, buffer, value):
        write_byte(buffer, value)


class Int2Field(ResourceField):
    block_description = '2-byte unsigned integer'

    @property
    def size(self):
        return 2

    def _read_internal(self, buffer, size, parent_read_data: dict = None):
        return read_short(buffer)

    def _write_internal(self, buffer, value):
        write_short(buffer, value)


class Int3Field(ResourceField):
    block_description = '3-byte unsigned integer'

    @property
    def size(self):
        return 3

    def _read_internal(self, buffer, size, parent_read_data: dict = None):
        return read_3int(buffer)

    def _write_internal(self, buffer, value):
        write_3int(buffer, value)


class BitmapField(ResourceField):
    block_description = '1-byte field, set of 8 flags'
    masks = [pow(2, 7 - i) for i in range(8)]

    @property
    def size(self):
        return 1

    def __init__(self, flag_names: list[str] = None, **kwargs):
        super().__init__(flag_names=flag_names,
                         **kwargs)
        self.flag_names = flag_names

    def _read_internal(self, buffer, size, parent_read_data: dict = None):
        value = read_byte(buffer)
        return {(self.flag_names[i] if self.flag_names else str(i)): bool(value & mask) for (i, mask) in
                enumerate(self.masks)}

    def _write_internal(self, buffer, value):
        raise NotImplementedError


class RequiredByteField(ByteField):

    def __init__(self, required_value: int, **kwargs):
        super().__init__(required_value=required_value,
                         **kwargs)
        self.required_value = required_value
        self.block_description = f'Always == {hex(self.required_value)}'

    def _read_internal(self, buffer, size, parent_read_data: dict = None):
        value = super()._read_internal(buffer, size, parent_read_data)
        if value != self.required_value:
            raise BlockIntegrityException(f'Expected {hex(self.required_value)}, found {hex(value)}')
        return value


class ArrayField(ResourceField):
    child = None

    @property
    def size(self):
        if self.length is None:
            return 0
        return self.child.size * self.length

    @property
    def min_size(self):
        if self.length is None:
            return 0
        return self.child.min_size * self.length if self.length_strategy == "strict" else 0

    @property
    def max_size(self):
        if self.length is None:
            return float('inf')
        return self.child.max_size * self.length

    @property
    def is_optional(self):
        return self.length_strategy == "read_available" or (
            self.length_strategy == "strict" and self.length == 0
        )

    def __init__(self,
                 child: ResourceField,
                 length: int = None,
                 length_strategy: Literal["strict", "read_available"] = "strict",
                 length_label: str = None,
                 **kwargs):
        super().__init__(child=child,
                         length=length,
                         length_strategy=length_strategy,
                         length_label=length_label,
                         **kwargs)
        self.child = child
        self.length = length
        self.length_strategy = length_strategy
        if length_label is None:
            if self.length is None:
                length_label = '?'
            elif self.length_strategy == "read_available":
                length_label = f'0..{self.length}'
            else:
                length_label = str(self.length)
        self.length_label = length_label
        self.block_description = f'Array of {length_label} items'

    def _read_internal(self, buffer, size, parent_read_data: dict = None):
        res = []
        amount = self.length
        if self.length is None and self.length_strategy != "read_available":
            raise BlockDefinitionException('Array field length is unknown')
        if self.length_strategy == "read_available":
            amount = (min(amount, floor(size / self.child.size))
                      if amount is not None
                      else floor(size / self.child.size))
        start = buffer.tell()
        try:
            res = self.child.read_multiple(buffer, size, amount, parent_read_data)
            size -= (buffer.tell() - start)
        except (NotImplementedError, EndOfBufferException) as ex:
            buffer.seek(start)
            for _ in range(amount):
                start = buffer.tell()
                try:
                    res.append(self.child.read(buffer, size))
                except EndOfBufferException as ex:
                    if self.length_strategy == "read_available":
                        # assume this array is finished
                        buffer.seek(start)
                        return res
                    else:
                        raise ex
                size -= (buffer.tell() - start)
        return res

    def _write_internal(self, buffer, value):
        for item in value:
            self.child.write(buffer, item)


from .colors import (Color24BitDosField,
                     Color24BitLittleEndianField,
                     Color24BitBigEndianField,
                     Color32BitField,
                     Color16Bit0565Field,
                     )
