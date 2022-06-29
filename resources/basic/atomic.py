from abc import ABC
from io import BufferedReader, BytesIO
from typing import Literal

from resources.basic.exceptions import BlockIntegrityException, EndOfBufferException, MultiReadUnavailableException
from resources.basic.read_block import ReadBlock
from resources.utils import represent_value_as_str


# block with static size and primitive output type
class AtomicReadBlock(ReadBlock, ABC):

    @property
    def size(self):
        return self.static_size

    def __init__(self, required_value: int = None, static_size: int = 1, **kwargs):
        super().__init__(required_value=required_value,
                         static_size=static_size,
                         **kwargs)
        self.required_value = required_value
        self.static_size = static_size
        if self.required_value is not None:
            label = f'Always == {represent_value_as_str(self.required_value)}'
            if self.block_description:
                self.block_description += '. ' + label
            else:
                self.block_description = label

    def read(self, buffer: [BufferedReader, BytesIO], size: int, parent_read_data: dict = None):
        value = super().read(buffer, size, parent_read_data)
        if self.required_value and value != self.required_value:
            raise BlockIntegrityException(f'Expected {represent_value_as_str(self.required_value)}, '
                                          f'found {represent_value_as_str(value)}')
        return value

    def read_multiple(self, buffer: [BufferedReader, BytesIO], size: int, length: int, parent_read_data: dict = None):
        if self.size != self.min_size or self.size != self.max_size:
            raise MultiReadUnavailableException()
        if self.size * length > size:
            raise EndOfBufferException(f'Cannot read multiple {self.__class__.__name__}: '
                                       f'min size {self.size * length}, available: {size}')
        bts = buffer.read(self.size * length)
        return [self.from_raw_value(x) for x in [bts[i*self.size:(i + 1)*self.size] for i in range(length)]]


class IntegerField(AtomicReadBlock):

    def __init__(self, static_size: int, is_signed: bool = False, byte_order: Literal["little", "big"] = "little",
                 **kwargs):
        self.is_signed = is_signed
        self.byte_order = byte_order
        self.block_description = f'{static_size}-byte{"s" if static_size > 1 else ""} ' \
                                 f'{"un" if not self.is_signed else ""}signed integer'
        if static_size > 1:
            self.block_description += f' ({byte_order} endian)'
        super(IntegerField, self).__init__(static_size=static_size,
                                           is_signed=is_signed,
                                           byte_order=byte_order,
                                           **kwargs)

    def from_raw_value(self, raw: bytes):
        return int.from_bytes(raw.ljust(self.size, b'\0'), byteorder=self.byte_order, signed=self.is_signed)

    def to_raw_value(self, value) -> bytes:
        return value.to_bytes(self.size, byteorder=self.byte_order, signed=self.is_signed).ljust(self.size, b'\0')


class Utf8Field(AtomicReadBlock):

    def __init__(self, length: int = None, **kwargs):
        self.block_description = 'UTF-8 string'
        super().__init__(length=length,
                         **kwargs)
        self.length = length

    @property
    def size(self):
        return self.length

    def from_raw_value(self, raw: bytes):
        return raw.decode('utf-8')

    def to_raw_value(self, value) -> bytes:
        return value.decode('utf-8')
