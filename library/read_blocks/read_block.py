from abc import ABC, abstractmethod
from io import BufferedReader, BytesIO, BufferedWriter
from typing import Literal

from library.helpers.exceptions import EndOfBufferException

# TODO
# new flow with separate data, state
# ----- remove instantiate_kwargs

# revisit below
# ----- optimize memory usage
# ----- write/flush new API
# ----- new size: number or ranges
# ----- all blocks cannot be read twice
# ----- cleanup blocks (recursively)
# ----- id should be set on init and never change
# ----- @cachedproperty parent, get from factory cache by id
# ----- optimize again
# ----- document blocks
# ----- link to offsets in explicit offsets block so can modify them automatically on editing
from library.read_data import ReadData


class ReadBlock(ABC):
    # those fields used for documentation only
    block_description = None
    description = None

    @property
    def id(self):
        return self._id

    def __init__(self, id: str = None, description: str = '', error_handling_strategy: Literal["raise", "return"] = "raise", **kwargs):
        self.instantiate_kwargs = {
            'description': description,
            'error_handling_strategy': error_handling_strategy,
            **kwargs,
        }
        self.description = description
        self.error_handling_strategy = error_handling_strategy
        self._id = id

    @property
    def size(self):
        return None

    @property
    def min_size(self):
        return self.size

    @property
    def max_size(self):
        return self.size

    def _check_length_before_reading(self, available_size: int):
        if self.min_size is not None and self.min_size > available_size:
            raise EndOfBufferException(f'Cannot read {self.__class__.__name__}: '
                                       f'min size {self.min_size}, available: {available_size}')

    def read(self, buffer: [BufferedReader, BytesIO], size: int, parent_read_data: dict = None) -> ReadData:
        try:
            self._check_length_before_reading(size)
            value = self._load_value(buffer, size, parent_read_data)
            self.value = self.from_raw_value(value)
            return ReadData(value=self.from_raw_value(value), block=self, block_state=self.persist_state())
        except Exception as ex:
            if self.error_handling_strategy == 'raise':
                raise ex
            else:
                return ex

    def write(self, buffer: BufferedWriter):
        self._flush_value(buffer, self.to_raw_value(self.value))

    def _load_value(self, buffer: [BufferedReader, BytesIO], size: int, parent_read_data: dict = None) -> bytes:
        return buffer.read(size if self.size is None else self.size)

    def _flush_value(self, buffer: BufferedWriter, bts: bytes):
        buffer.write(bts)

    @abstractmethod
    def from_raw_value(self, raw: bytes):
        pass

    @abstractmethod
    def to_raw_value(self, value, offset=0) -> bytes:
        pass

    @abstractmethod
    def persist_state(self) -> dict:
        return dict()

    @abstractmethod
    def apply_state(self, state: dict) -> None:
        pass
