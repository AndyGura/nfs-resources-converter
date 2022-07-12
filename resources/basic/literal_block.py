from copy import deepcopy
from io import BufferedReader, BytesIO
from typing import List

from resources.basic.compound_block import CompoundBlock
from resources.basic.delegate_block import DelegateBlock
from resources.basic.exceptions import BlockIntegrityException


class LiteralResource(DelegateBlock):

    @property
    def min_size(self):
        return super().min_size or min(x.min_size for x in self.possible_resources)

    @property
    def max_size(self):
        return super().max_size or max(x.max_size for x in self.possible_resources)

    @property
    def Fields(self):
        return self.delegated_block.Fields

    def __init__(self, possible_resources: List[CompoundBlock], **kwargs):
        super().__init__(possible_resources=possible_resources,
                         **kwargs)
        self.possible_resources = deepcopy(possible_resources)
        self.persistent_data = None

    def read(self, buffer: [BufferedReader, BytesIO], size: int, parent_read_data: dict = None):
        if self.delegated_block is None:
            from guess_parser import probe_block_class
            block_class = probe_block_class(buffer, resources_to_pick=[x.__class__ for x in self.possible_resources])
            if not block_class:
                raise BlockIntegrityException('Expectation failed for literal block while reading: class not found')
            for res in self.possible_resources:
                if isinstance(res, block_class):
                    self.delegated_block = deepcopy(res)
                    break
        return super().read(buffer, size, parent_read_data)
