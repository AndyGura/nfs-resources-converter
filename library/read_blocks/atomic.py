from abc import ABC
from io import BufferedReader, BytesIO
from typing import Literal, List, Tuple

from library.helpers.exceptions import BlockIntegrityException, MultiReadUnavailableException, EndOfBufferException
from library.read_blocks.read_block import ReadBlock
from library.utils import represent_value_as_str


class AtomicReadBlock(ReadBlock, ABC):
    """block with static size, no id and primitive output type. Can be reused many times while reading resource"""

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

    def __deepcopy__(self, memo):
        return self

    def read(self, buffer: [BufferedReader, BytesIO], size: int, parent_read_data: dict = None):
        value = super().read(buffer, size, parent_read_data)
        if self.required_value and value != self.required_value:
            raise BlockIntegrityException(f'Expected {represent_value_as_str(self.required_value)}, '
                                          f'found {represent_value_as_str(value)}')
        return value

    def read_multiple(self, buffer: [BufferedReader, BytesIO], size: int, length: int, parent_read_data: dict = None):
        self_size = self.size  # optimization
        if self_size != self.min_size or self_size != self.max_size:
            raise MultiReadUnavailableException()
        if self_size * length > size:
            raise EndOfBufferException(f'Cannot read multiple {self.__class__.__name__}: '
                                       f'min size {self_size * length}, available: {size}')
        bts = buffer.read(self_size * length)
        return [self.from_raw_value(x) for x in [bts[i * self_size:(i + 1) * self_size] for i in range(length)]]


class IntegerBlock(AtomicReadBlock):

    def __init__(self, static_size: int, is_signed: bool = False, byte_order: Literal["little", "big"] = "little",
                 **kwargs):
        self.is_signed = is_signed
        self.byte_order = byte_order
        self.block_description = f'{static_size}-byte{"s" if static_size > 1 else ""} ' \
                                 f'{"un" if not self.is_signed else ""}signed integer'
        if static_size > 1:
            self.block_description += f' ({byte_order} endian)'
        super(IntegerBlock, self).__init__(static_size=static_size,
                                           is_signed=is_signed,
                                           byte_order=byte_order,
                                           **kwargs)

    # optimized case with unsigned 8-bit ints
    def read_multiple(self, buffer: [BufferedReader, BytesIO], size: int, length: int, parent_read_data: dict = None):
        self_size = self.size  # optimization
        if self_size != self.min_size or self_size != self.max_size:
            raise MultiReadUnavailableException()
        if self_size * length > size:
            raise EndOfBufferException(f'Cannot read multiple {self.__class__.__name__}: '
                                       f'min size {self_size * length}, available: {size}')
        bts = buffer.read(self_size * length)
        # here is optimization
        if self_size == 1 and not self.is_signed:
            return list(bts)
        else:
            return [self.from_raw_value(x) for x in [bts[i * self_size:(i + 1) * self_size] for i in range(length)]]

    def from_raw_value(self, raw: bytes):
        self_size = self.size
        return int.from_bytes(raw.ljust(self_size, b'\0') if self_size > 1 else raw, byteorder=self.byte_order,
                              signed=self.is_signed)

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
        return value.encode('utf-8')


class BytesField(AtomicReadBlock):
    # TODO maybe I can replace block_description with pure python documentation?
    block_description = ""

    def __init__(self, length: int = None,
                 **kwargs):
        kwargs['length'] = length
        super().__init__(**kwargs)
        self.length = length

    @property
    def size(self):
        return self.length

    @property
    def min_size(self):
        return 0

    @property
    def max_size(self):
        if self.length is None:
            return float('inf')
        return self.length

    def from_raw_value(self, raw: bytes):
        return raw

    def to_raw_value(self, value) -> bytes:
        return value


class BitFlagsBlock(IntegerBlock, ABC):
    def __init__(self, flag_names: List[Tuple[int, str]], **kwargs):
        kwargs['static_size'] = 1
        kwargs['is_signed'] = False
        super().__init__(flag_names=flag_names,
                         **kwargs)
        self.flag_names = flag_names
        self.flag_name_map = [str(i) for i in range(8)]
        for value, name in self.flag_names:
            self.flag_name_map[value] = name
        self.block_description = (
                    '8 flags container<br/><details><summary>flag names (from least to most significant)</summary>'
                    + '<br/>'.join(
                [f'{i}: {x}' for i, x in enumerate(self.flag_name_map) if x != str(i)]) + '</details>')

    def from_raw_value(self, raw: bytes):
        flags = super().from_raw_value(raw)
        res = {}
        for i in range(8):
            res[self.flag_name_map[i]] = bool(flags & (1 if i == 0 else 1 << i))
        return res

    def to_raw_value(self, value) -> bytes:
        res = 0
        for i in range(8):
            if value[i]:
                res = res | (1 << i)
        return super().to_raw_value(res)


class EnumByteBlock(IntegerBlock, ABC):
    def __init__(self, enum_names: List[Tuple[int, str]], **kwargs):
        kwargs['static_size'] = 1
        kwargs['is_signed'] = False
        super().__init__(enum_names=enum_names,
                         **kwargs)
        self.enum_names = enum_names
        self.enum_name_map = [str(i) for i in range(256)]
        for value, name in self.enum_names:
            self.enum_name_map[value] = name
        self.block_description = ('Enum of 256 possible values<br/><details><summary>Value names:</summary>'
                                  + '<br/>'.join(
                    [f'{i}: {x}' for i, x in enumerate(self.enum_name_map) if x != str(i)]) + '</details>')

    def from_raw_value(self, raw: bytes):
        return self.enum_name_map[super().from_raw_value(raw)]

    def to_raw_value(self, value) -> bytes:
        return super().to_raw_value(self.enum_name_map.index(value))
