from abc import ABC, abstractmethod
from io import BufferedReader, BytesIO
from typing import Literal

from resources.basic.exceptions import EndOfBufferException, BlockIntegrityException


class ReadBlock(ABC):
    # those fields used for documentation only
    block_description = None
    description = None
    is_unknown = False

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        self._id = value

    def __init__(self, description: str = '', is_unknown: bool = False,
                 error_handling_strategy: Literal["raise", "return"] = "raise", **kwargs):
        self.instantiate_kwargs = {
            'description': description,
            'is_unknown': is_unknown,
            'error_handling_strategy': error_handling_strategy,
            **kwargs,
        }
        self.description = description
        self.is_unknown = is_unknown
        self.error_handling_strategy = error_handling_strategy
        self._id = None
        if not self.description and self.is_unknown:
            self.description = 'Unknown purpose'

    # we need a fast copy operation because block instance should be created for every single readable block
    def __deepcopy__(self, memo):
        return self.__class__(**self.instantiate_kwargs)

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

    def read(self, buffer: [BufferedReader, BytesIO], size: int, parent_read_data: dict = None):
        try:
            self._check_length_before_reading(size)
            value = self.load_value(buffer, size, parent_read_data)
            return self.from_raw_value(value)
        except Exception as ex:
            if self.error_handling_strategy == 'raise':
                raise ex
            else:
                return ex

    def load_value(self, buffer: [BufferedReader, BytesIO], size: int, parent_read_data: dict = None):
        return buffer.read(size if self.size is None else self.size)

    @abstractmethod
    def from_raw_value(self, raw: bytes):
        pass

    @abstractmethod
    def to_raw_value(self, value) -> bytes:
        pass
