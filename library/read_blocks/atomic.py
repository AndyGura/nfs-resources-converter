from abc import ABC
from io import BufferedReader, BytesIO
from typing import Literal, List, Tuple

from library.helpers.exceptions import BlockIntegrityException, EndOfBufferException
from library.read_blocks.read_block import ReadBlock
from library.read_data import ReadData
from library.utils import represent_value_as_str


class AtomicReadBlock(ReadBlock, ABC):
    """Block with static size"""

    def get_size(self, state):
        return self.static_size

    def __init__(self, required_value: int = None, static_size: int = 1, **kwargs):
        super().__init__(**kwargs)
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

    def read(self, buffer: [BufferedReader, BytesIO], size: int, state: dict):
        data = super().read(buffer, size, state)
        if self.required_value and data.value != self.required_value:
            raise BlockIntegrityException(f'Expected {represent_value_as_str(self.required_value)}, '
                                          f'found {represent_value_as_str(data.value)}')
        return data

    def read_multiple(self, buffer: [BufferedReader, BytesIO], size: int, states: List[dict], length: int):
        self_size = self.static_size
        if self_size * length > size:
            raise EndOfBufferException(f'Cannot read multiple {self.__class__.__name__}: '
                                       f'min size {self_size * length}, available: {size}')
        bts = buffer.read(self_size * length)
        if self.simplified:
            return [self.from_raw_value(x, None) for x in [bts[i * self_size:(i + 1) * self_size] for i in range(length)]]
        return [self.wrap_result(self.from_raw_value(x, state), state)
                for x, i, state in [(bts[i * self_size:(i + 1) * self_size],
                                     i,
                                     states[i] if len(states) > i else None)
                                    for i in range(length)
                                    ]]


class IntegerBlock(AtomicReadBlock):

    @property
    def size(self):
        return 0

    def __init__(self, static_size: int, is_signed: bool = False, byte_order: Literal["little", "big"] = "little",
                 **kwargs):
        self.is_signed = is_signed
        self.byte_order = byte_order
        self.block_description = f'{static_size}-byte{"s" if static_size > 1 else ""} ' \
                                 f'{"un" if not self.is_signed else ""}signed integer'
        if static_size > 1:
            self.block_description += f' ({byte_order} endian)'
        super(IntegerBlock, self).__init__(static_size=static_size, **kwargs)

    def read_multiple(self, buffer: [BufferedReader, BytesIO], size: int, states: List[dict], length: int):
        # insane speedup in this case (we check class name to not avoid from_raw_value in subclasses)
        if self.simplified and self.static_size == 1 and not self.is_signed and self.__class__.__name__ == 'IntegerBlock':
            if length > size:
                raise EndOfBufferException(f'Cannot read multiple {self.__class__.__name__}: '
                                           f'min size {length}, available: {size}')
            return list(buffer.read(length))
        return super().read_multiple(buffer, size, states, length)

    def from_raw_value(self, raw: bytes, state: dict):
        return int.from_bytes(raw.ljust(self.static_size, b'\0') if self.static_size > 1 else raw,
                              byteorder=self.byte_order,
                              signed=self.is_signed)

    def to_raw_value(self, data: ReadData, state) -> bytes:
        return data.value.to_bytes(self.static_size, byteorder=self.byte_order, signed=self.is_signed).ljust(
            self.static_size, b'\0')


class Utf8Field(AtomicReadBlock):

    def __init__(self, length: int = None, **kwargs):
        super().__init__(**kwargs)
        self.length = length
        self.block_description = 'UTF-8 string'

    def get_size(self, state):
        return self.length

    def from_raw_value(self, raw: bytes, state: dict):
        return raw.decode('utf-8')

    def to_raw_value(self, data, state) -> bytes:
        return data.encode('utf-8')


class BytesField(AtomicReadBlock):
    block_description = ""

    def __init__(self,
                 length: int = None,
                 length_strategy: Literal["strict", "read_available"] = "strict",
                 **kwargs):
        super().__init__(**kwargs)
        self.length = length
        self.length_strategy = length_strategy

    def get_size(self, state):
        return self.length

    def get_min_size(self, state):
        return 0

    def get_max_size(self, state):
        if self.length is None:
            return float('inf')
        return self.length

    def from_raw_value(self, raw: bytes, state: dict):
        return raw

    def to_raw_value(self, data, state) -> bytes:
        return data


class BitFlagsBlock(IntegerBlock, ABC):
    def __init__(self, flag_names: List[Tuple[int, str]], **kwargs):
        super().__init__(static_size=1,
                         is_signed=False,
                         **kwargs)
        self.flag_names = flag_names
        self.flag_name_map = [str(i) for i in range(8)]
        for value, name in self.flag_names:
            self.flag_name_map[value] = name
        self.block_description = (
                '8 flags container<br/><details><summary>flag names (from least to most significant)</summary>'
                + '<br/>'.join(
            [f'{i}: {x}' for i, x in enumerate(self.flag_name_map) if x != str(i)]) + '</details>')

    def from_raw_value(self, raw: bytes, state: dict):
        flags = super().from_raw_value(raw, state)
        res = {}
        for i in range(8):
            res[self.flag_name_map[i]] = bool(flags & (1 if i == 0 else 1 << i))
        return res

    def to_raw_value(self, data, state) -> bytes:
        res = 0
        for i in range(8):
            if data[self.flag_name_map[i]]:
                res = res | (1 << i)
        return super().to_raw_value(res)


class EnumByteBlock(IntegerBlock, ABC):
    def __init__(self, enum_names: List[Tuple[int, str]], **kwargs):
        super().__init__(static_size=1,
                         is_signed=False,
                         **kwargs)
        self.enum_names = enum_names
        self.enum_name_map = [str(i) for i in range(256)]
        for value, name in self.enum_names:
            self.enum_name_map[value] = name
        self.block_description = ('Enum of 256 possible values<br/><details><summary>Value names:</summary>'
                                  + '<br/>'.join(
                    [f'{i}: {x}' for i, x in enumerate(self.enum_name_map) if x != str(i)]) + '</details>')

    def from_raw_value(self, raw: bytes, state: dict):
        return self.enum_name_map[super().from_raw_value(raw, state)]

    def to_raw_value(self, data, state) -> bytes:
        return super().to_raw_value(self.enum_name_map.index(data))
