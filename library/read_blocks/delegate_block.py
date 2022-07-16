from io import BufferedReader, BytesIO

from library.read_blocks.exceptions import BlockDefinitionException
from library.read_blocks.read_block import ReadBlock


class DelegateBlock(ReadBlock):
    """A block class, which uses functionality of another block class"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._delegated_block = None

    def __getattr__(self, name):
        if self._delegated_block and hasattr(self._delegated_block, name):
            return getattr(self._delegated_block, name)
        return object.__getattribute__(self, name)

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        self._id = value
        if self.delegated_block:
            self.delegated_block.id = self.id

    @property
    def delegated_block(self) -> ReadBlock:
        return self._delegated_block

    @delegated_block.setter
    def delegated_block(self, value):
        self._delegated_block = value
        value.id = self.id

    @property
    def size(self):
        return (self._delegated_block.size
                if self._delegated_block is not None
                else None)

    @property
    def min_size(self):
        return (self._delegated_block.min_size
                if self._delegated_block is not None
                else None)

    @property
    def max_size(self):
        return (self._delegated_block.max_size
                if self._delegated_block is not None
                else None)

    def load_value(self, buffer: [BufferedReader, BytesIO], size: int, parent_read_data: dict = None):
        if not self._delegated_block:
            raise BlockDefinitionException('Delegated block not defined')
        return self._delegated_block.load_value(buffer, size, parent_read_data)

    def read(self, buffer: [BufferedReader, BytesIO], size: int, parent_read_data: dict = None):
        try:
            if not self._delegated_block:
                raise BlockDefinitionException('Delegated block not defined')
            return self._delegated_block.read(buffer, size, parent_read_data)
        except Exception as ex:
            if self.error_handling_strategy == 'return':
                return ex
            else:
                raise ex

    def from_raw_value(self, raw: bytes):
        if not self._delegated_block:
            raise BlockDefinitionException('Delegated block not defined')
        return self._delegated_block.from_raw_value(raw)

    def to_raw_value(self, value) -> bytes:
        if not self._delegated_block:
            raise BlockDefinitionException('Delegated block not defined')
        return self._delegated_block.to_raw_value(value)
