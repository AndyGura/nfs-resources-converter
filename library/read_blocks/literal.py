from copy import deepcopy
from io import BufferedReader, BytesIO
from typing import List

from library.read_blocks.compound import CompoundBlock
from library.read_blocks.delegate import DelegateBlock
from library.helpers.exceptions import BlockIntegrityException


class LiteralBlock(DelegateBlock):

    @property
    def min_size(self):
        try:
            return super().min_size or min(x.min_size for x in self.possible_resources)
        except TypeError:
            return 0

    @property
    def max_size(self):
        return super().max_size or max(x.max_size for x in self.possible_resources)

    @property
    def Fields(self):
        return self.delegated_block.Fields

    def __init__(self, possible_resources: List[CompoundBlock], **kwargs):
        super().__init__(possible_resources=possible_resources,
                         **kwargs)
        # TODO no need to copy them here. Copy only delegated block
        self.possible_resources = deepcopy(possible_resources)

    def read(self, buffer: [BufferedReader, BytesIO], size: int, parent_read_data: dict = None):
        try:
            if self.delegated_block is None:
                from library import probe_block_class
                block_class = probe_block_class(buffer, resources_to_pick=[x.__class__ for x in self.possible_resources])
                if not block_class:
                    raise BlockIntegrityException('Expectation failed for literal block while reading: class not found')
                for res in self.possible_resources:
                    if isinstance(res, block_class):
                        self.delegated_block = deepcopy(res)
                        break
            return super().read(buffer, size, parent_read_data)
        except Exception as ex:
            if self.error_handling_strategy == 'return':
                return ex
            else:
                raise ex
