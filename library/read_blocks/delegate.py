from io import BufferedReader, BytesIO

from library.helpers.exceptions import BlockDefinitionException
from library.read_blocks.read_block import ReadBlock


class DelegateBlock(ReadBlock):
    """A block class, which uses functionality of another block class. Block class is initially unknown when defining block"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get_size(self, state):
        delegated_block = state.get('delegated_block')
        return (delegated_block.size
                if delegated_block is not None
                else None)

    def get_min_size(self, state):
        delegated_block = state.get('delegated_block')
        return (delegated_block.min_size
                if delegated_block is not None
                else None)

    def get_max_size(self, state):
        delegated_block = state.get('delegated_block')
        return (delegated_block.max_size
                if delegated_block is not None
                else None)

    def _load_value(self, buffer: [BufferedReader, BytesIO], size: int, state: dict, parent_read_data: dict = None):
        delegated_block = state.get('delegated_block')
        if not delegated_block:
            raise BlockDefinitionException('Delegated block not defined')
        return delegated_block._load_value(buffer, size, state, parent_read_data)

    def read(self, buffer: [BufferedReader, BytesIO], size: int, state: dict, parent_read_data: dict = None):
        delegated_block = state.get('delegated_block')
        try:
            if not delegated_block:
                raise BlockDefinitionException('Delegated block not defined')
            return delegated_block.read(buffer, size, state, parent_read_data)
        except Exception as ex:
            if self.error_handling_strategy == 'return':
                return ex
            else:
                raise ex

    def from_raw_value(self, raw: bytes, state: dict):
        delegated_block = state.get('delegated_block')
        if not delegated_block:
            raise BlockDefinitionException('Delegated block not defined')
        return delegated_block.from_raw_value(raw)

    def to_raw_value(self, data, state) -> bytes:
        delegated_block = state.get('delegated_block')
        if not delegated_block:
            raise BlockDefinitionException('Delegated block not defined')
        return delegated_block.to_raw_value(data)
