from io import BufferedReader, BytesIO
from typing import List

from library.read_blocks.compound import CompoundBlock
from library.read_blocks.delegate import DelegateBlock
from library.helpers.exceptions import DataIntegrityException


class LiteralBlock(DelegateBlock):

    def get_min_size(self, state):
        try:
            return super().get_min_size(state) or min(x.get_min_size(state) for x in self.possible_resources)
        except TypeError:
            return 0

    def get_max_size(self, state):
        return super().get_max_size(state) or max(x.get_max_size(state) for x in self.possible_resources)

    def get_size(self, state):
        selected_size = super().get_size(state)
        if selected_size is not None:
            return selected_size
        sizes = [x.get_size(state) for x in self.possible_resources]
        # if all equal
        if sizes.count(sizes[0]) == len(sizes):
            return sizes[0]
        return None

    @property
    def Fields(self):
        return self.delegated_block.Fields

    def __init__(self, possible_resources: List[CompoundBlock], **kwargs):
        super().__init__(**kwargs)
        self.possible_resources = possible_resources

    def read(self, buffer: [BufferedReader, BytesIO], size: int, state: dict):
        delegated_block = state.get('delegated_block')
        try:
            if delegated_block is None:
                from library import probe_block_class
                block_class = probe_block_class(buffer, resources_to_pick=[x.__class__ for x in self.possible_resources])
                if not block_class:
                    raise DataIntegrityException('Expectation failed for literal block while reading: class not found')
                for res in self.possible_resources:
                    if isinstance(res, block_class):
                        state['delegated_block'] = res
                        break
            return super().read(buffer, size, state)
        except Exception as ex:
            if self.error_handling_strategy == 'return':
                return ex
            else:
                raise ex
