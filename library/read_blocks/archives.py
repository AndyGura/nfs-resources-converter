from abc import ABC

from library.read_blocks import CompoundBlock, DeclarativeCompoundBlock, BytesBlock, UTF8Block


# Base abstract class for archive blocks
# Subclasses should:
# 1) Provide item block to super().__init__
# 2) Declare own compound block fields as usual, documentation and io friendly
# 3) Declare fields like children offsets, children array etc. usage to be "io,doc" (skip showing in UI)
# 4) Add `children = (ArrayBlock(child=None, length=None), {'usage': 'ui'})` to Fields class
# 5) Update read function to produce "children" array as per structure, implemented here
# 6) Update write function to use "children" array as per structure, and transform it to the io format
# 7) Override estimate_packed_size (look at shpi example)
class ArchiveBlock(DeclarativeCompoundBlock, ABC):
    def __init__(self, item_block, alias_field=None, **kwargs):
        super().__init__(**kwargs)
        self.item_block = item_block
        fields = [('item', item_block, {}),
                  ('pre_offset_payload', BytesBlock(length=None), {}),
                  ('post_offset_payload', BytesBlock(length=None), {})]
        if alias_field is not None:
            fields.append(('alias', alias_field, {}))
        self.field_blocks_map['children'].child = CompoundBlock(fields=fields)
