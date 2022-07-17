from copy import deepcopy
from io import BufferedReader, BytesIO

from library.read_blocks.delegate import DelegateBlock
from library.helpers.exceptions import BlockDefinitionException
from library.read_blocks.read_block import ReadBlock


class DetachedBlock(DelegateBlock):

    def __init__(self, block: ReadBlock, **kwargs):
        self.block = deepcopy(block)
        kwargs['block'] = block
        super().__init__(**kwargs)
        self.offset = None
        self._size = None
        self.delegated_block = block

    @property
    def size(self):
        return self._size

    @size.setter
    def size(self, value):
        self._size = value

    def read(self, buffer: [BufferedReader, BytesIO], size: int, parent_read_data: dict = None):
        if self.offset is None:
            raise BlockDefinitionException('Unknown offset of detached block')
        if self.size is None:
            raise BlockDefinitionException('Unknown size of detached block')
        ptr = buffer.tell()
        buffer.seek(self.offset)
        # ignoring incoming size, we are detached from block
        res = super().read(buffer, self.size, parent_read_data)
        buffer.seek(ptr)
        return res
