import traceback
from abc import ABC, abstractmethod
from io import BufferedReader, BytesIO, BufferedWriter
from typing import Literal

import settings
from library.helpers.exceptions import EndOfBufferException
# ----- new size: number or ranges
# ----- @cachedproperty parent, get from factory cache by id
# ----- optimize again
# ----- document blocks
# ----- link to offsets in explicit offsets block so can modify them automatically on editing
from library.read_data import ReadData


# TODO
# ----- Utilize read data class
# ----- write/flush new API
# ----- completely remove copying fields
# ----- remove instantiate_kwargs
# ----- memory usage
# ----- rename "read-block" to "data-block" in all classes


class DataBlock(ABC):
    """A base abstract class for data block."""
    block_description = None

    def __init__(self, description: str = '', error_handling_strategy: Literal["raise", "return"] = "raise",
                 simplified: bool = False):
        """
         :param description: The description of this block's data, when used as subblock
         :type description: str
         :param error_handling_strategy: What to do with errors, if happen during reading: raise or return as result
         :type error_handling_strategy: Literal["raise", "return"], defaults to "raise"
         :param simplified: If true, pure value returned, else wrapped to ReadData class instance
         :type simplified: bool, defaults to False
         """
        self.description = description
        self.error_handling_strategy = error_handling_strategy
        self.simplified = simplified

    def get_size(self, state) -> Literal[int, None]:
        """
         Gets size of block in bytes, according to state. Can return None if unknown
         :param state: The state of data block
         :type state: dict
         :rtype int
         """
        return None

    def get_min_size(self, state) -> Literal[int, None]:
        """
         Gets minimum size of block in bytes, according to state. Can return None if unknown
         :param state: The state of data block
         :type state: dict
         :rtype int
         """
        return self.get_size(state)

    def get_max_size(self, state) -> Literal[int, None]:
        """
         Gets maxumum size of block in bytes, according to state. Can return None if unknown
         :param state: The state of data block
         :type state: dict
         :rtype int
         """
        return self.get_size(state)

    def wrap_result(self, value, block_state=None):
        """
         Wraps result into final form
         """
        if self.simplified:
            return value
        else:
            return ReadData(value=value, block=self, block_state=block_state)

    def unwrap_result(self, data: ReadData):
        """
         Unwraps value from final result form
         """
        if self.simplified:
            return data
        else:
            return data.value

    def read(self, buffer: [BufferedReader, BytesIO], size: int, state: dict) -> ReadData:
        try:
            min_size = self.get_min_size(state)
            if min_size is not None and min_size > size:
                raise EndOfBufferException(f'Cannot read {self.__class__.__name__}: '
                                           f'min size {min_size}, available: {size}')
            value = self._load_value(buffer, size, state)
            return self.wrap_result(value=self.from_raw_value(value, state), block_state=state)
        except Exception as ex:
            if settings.print_errors:
                traceback.print_exc()
            if self.error_handling_strategy == 'raise':
                raise ex
            else:
                return ex

    def _load_value(self, buffer: [BufferedReader, BytesIO], size: int, state: dict) -> bytes:
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
    def to_raw_value(self, data: ReadData, offset=0) -> bytes:  # TODO offset to state?
        pass
