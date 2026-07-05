from abc import ABC
from typing import List, Tuple

from library.read_blocks import CompoundBlock, DeclarativeCompoundBlock, ArrayBlock, DataBlock, BytesBlock, UTF8Block


# Base abstract class for archive blocks
# Subclasses should:
# 1) Provide item block to super().__init__
# 2) Declare own compound block fields as usual, documentation and io friendly
# 3) Declare fields like children offsets, children array etc. usage to be "io,doc" (skip showing in UI)
# 4) Fields class should be extended from ArchiveBlock.Fields, not DeclarativeCompoundBlock.Fields
# 5) Update read function to produce "children" array as per structure, implemented here
# 6) Update write function to use "children" array as per structure, and transform it to the io format
class ArchiveBlock(DeclarativeCompoundBlock, ABC):
    class Fields(DeclarativeCompoundBlock.Fields):
        children = (ArrayBlock(child=None, length=None),
                    {'usage': 'ui'})

        @classmethod
        @property
        def fields(cls) -> List[Tuple[str, DataBlock]]:
            fields = super().fields
            return fields + [('children', cls.children)]

    @property
    def item_block(self):
        return self._item_block

    def __init__(self, item_block, **kwargs):
        super().__init__(**kwargs)
        self._item_block = item_block
        self.field_blocks_map['children'].child = CompoundBlock(
            fields=[('item', item_block, {}),
                    ('alias', UTF8Block(length=None), {}),
                    ('pre_offset_payload', BytesBlock(length=None), {}),
                    ('post_offset_payload', BytesBlock(length=None), {})])
