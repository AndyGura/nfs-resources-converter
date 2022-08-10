import traceback
from abc import ABC, abstractmethod
from io import BufferedReader, BytesIO, BufferedWriter
from logging import error
from typing import Literal

import settings
from library.helpers.exceptions import EndOfBufferException

# TODO
# ----- Utilize read data class
# ----- write/flush new API
# ----- completely remove copying fields
# ----- remove instantiate_kwargs
# ----- memory usage

# ----- rename "read-block" to "data-block" in all classes

# ----- new size: number or ranges
# ----- @cachedproperty parent, get from factory cache by id
# ----- optimize again
# ----- document blocks
# ----- link to offsets in explicit offsets block so can modify them automatically on editing
from library.read_data import ReadData


class ReadBlock(ABC):
    # those fields used for documentation only
    block_description = None
    description = None

    def __init__(self, description: str = '', error_handling_strategy: Literal["raise", "return"] = "raise"):
        self.description = description
        self.error_handling_strategy = error_handling_strategy

    def get_size(self, state):
        return None

    def get_min_size(self, state):
        return self.get_size(state)

    def get_max_size(self, state):
        return self.get_size(state)

    def _check_length_before_reading(self, available_size: int, state: dict):
        min_size = self.get_min_size(state)
        if min_size is not None and min_size > available_size:
            raise EndOfBufferException(f'Cannot read {self.__class__.__name__}: '
                                       f'min size {min_size}, available: {available_size}')

    def read(self, buffer: [BufferedReader, BytesIO], size: int, state: dict, parent_read_data: dict = None) -> ReadData:
        try:
            self._check_length_before_reading(size, state)
            value = self._load_value(buffer, size, state, parent_read_data)
            return ReadData(value=self.from_raw_value(value, state), block=self, block_state=state)
        except Exception as ex:
            if settings.print_errors:
                traceback.print_exc()
            if self.error_handling_strategy == 'raise':
                raise ex
            else:
                return ex

    # TODO remove parent_read_data. Used only by AnyBitmapBlock, checking SHPI directory
    def _load_value(self, buffer: [BufferedReader, BytesIO], size: int, state: dict, parent_read_data: dict = None) -> bytes:
        self_size = self.get_size(state)
        return buffer.read(size if self_size is None else self_size)

    @abstractmethod
    def from_raw_value(self, raw: bytes, state: dict):
        pass

    def write(self, buffer: BufferedWriter, data: ReadData):
        self._flush_value(buffer, self.to_raw_value(data.value, data.block_state), data.block_state)

    def _flush_value(self, buffer: BufferedWriter, raw: bytes, state: dict = None):
        buffer.write(raw)

    @abstractmethod
    def to_raw_value(self, data: ReadData, state: dict = None, offset=0) -> bytes:  # TODO offset to state?
        pass
