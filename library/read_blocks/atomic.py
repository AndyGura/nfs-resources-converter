from abc import ABC
from io import BufferedReader, BytesIO
from typing import Literal, List, Tuple, Dict

from library.helpers.exceptions import BlockIntegrityException, EndOfBufferException
from library.read_blocks.data_block import DataBlock
from library.read_data import ReadData
from library.utils import represent_value_as_str


class AtomicDataBlock(DataBlock, ABC):
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
            return [self.from_raw_value(x, None) for x in
                    [bts[i * self_size:(i + 1) * self_size] for i in range(length)]]
        return [self.wrap_result(self.from_raw_value(x, state), state)
                for x, i, state in [(bts[i * self_size:(i + 1) * self_size],
                                     i,
                                     states[i] if len(states) > i else None)
                                    for i in range(length)
                                    ]]


class IntegerBlock(AtomicDataBlock):

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

    def get_editor_validators(self, state) -> Dict:
        return {
            **super().get_editor_validators(state),
            'min_value': self.from_raw_value(
                (-(1 << (self.static_size * 8 - 1))).to_bytes(self.static_size, byteorder=self.byte_order, signed=True)
                if self.is_signed
                else (b'\0' * self.static_size),
                state
            ),
            'max_value': self.from_raw_value((
                ((1 << (self.static_size * 8 - 1)) if self.is_signed else (1 << (self.static_size * 8))) - 1
              ).to_bytes(self.static_size, byteorder=self.byte_order, signed=self.is_signed),
              state
            ),
            'value_interval': self.from_raw_value(
                (1).to_bytes(self.static_size, byteorder=self.byte_order, signed=self.is_signed),
                state
            ),
        }

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

    def to_raw_value(self, data: ReadData) -> bytes:
        value = self.unwrap_result(data)
        return value.to_bytes(self.static_size, byteorder=self.byte_order, signed=self.is_signed).ljust(
            self.static_size, b'\0')


class Utf8Block(AtomicDataBlock):

    def __init__(self, length: int = None, **kwargs):
        if kwargs.get('required_value'):
            length = len(kwargs['required_value'])
        self.block_description = 'UTF-8 string'
        super().__init__(**kwargs)
        self.length = length

    def get_size(self, state):
        return self.length

    def from_raw_value(self, raw: bytes, state: dict):
        return raw.decode('utf-8')

    def to_raw_value(self, data: ReadData) -> bytes:
        value = self.unwrap_result(data)
        return value.encode('utf-8')

# FIXME it is not an atomic block, because has variable size. Split to two: AtomicByteField and ByteField
class BytesField(AtomicDataBlock):
    block_description = "Byte array"

    def __init__(self,
                 length: int = None,
                 length_strategy: Literal["strict", "read_available"] = "strict",
                 **kwargs):
        super().__init__(**kwargs)
        self.length = length
        self.length_strategy = length_strategy

    # FIXME hack for making it work as atomic block. Remove after refactoring
    @property
    def static_size(self):
        return self.length or 0

    @static_size.setter
    def static_size(self, v):
        pass

    def get_size(self, state):
        return self.length

    def get_min_size(self, state):
        return self.length if self.length is not None and self.length_strategy == "strict" else 0

    def get_max_size(self, state):
        if self.length is None:
            return float('inf')
        return self.length

    def from_raw_value(self, raw: bytes, state: dict):
        return raw

    def to_raw_value(self, data: ReadData) -> bytes:
        return self.unwrap_result(data)


class BitFlagsBlock(IntegerBlock, ABC):
    def __init__(self, flag_names: List[Tuple[int, str]], **kwargs):
        kwargs.pop('static_size', None)
        kwargs.pop('is_signed', None)
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

    def to_raw_value(self, data: ReadData) -> bytes:
        res = 0
        for i in range(8):
            if data[self.flag_name_map[i]]:
                res = res | (1 << i)
        return super().to_raw_value(self.wrap_result(res, data.block_state))


class EnumByteBlock(IntegerBlock, ABC):
    def __init__(self, enum_names: List[Tuple[int, str]], **kwargs):
        kwargs.pop('static_size', None)
        kwargs.pop('is_signed', None)
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

    def to_raw_value(self, data: ReadData) -> bytes:
        value = self.unwrap_result(data)
        return super().to_raw_value(self.wrap_result(self.enum_name_map.index(value), data.block_state))
