from library.read_blocks.atomic import IntegerBlock, Utf8Block
from library.read_blocks.compound import CompoundBlock


class TestResource(CompoundBlock):
    class Fields(CompoundBlock.Fields):
        resource_id = Utf8Block(required_value='TSTR')
        test_byte = IntegerBlock(static_size=1)
        test_char = Utf8Block(static_size=1)
