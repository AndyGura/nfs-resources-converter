from library.read_blocks import DeclarativeCompoundBlock, UTF8Block, IntegerBlock, DelegateBlock


# A test resource with common complications for testing read, write and GUI functionality
class TestResource(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        # various strings
        required_string = (UTF8Block(length=4, required_value='NRCT'),
                           {'description': 'Test text field with required value'})
        fixed_size_string = (UTF8Block(length=12),
                             {'description': 'Test text field with fixed length'})
        # various numbers
        ubyte = (IntegerBlock(length=1),
                 {'description': 'Test 0 - 255 number'})
        byte = (IntegerBlock(length=1, is_signed=True),
                {'description': 'Test -128 - 127 number'})
        ushort = (IntegerBlock(length=2),
                  {'description': 'Test 0 - 65535 number'})
        ushort_big = (IntegerBlock(length=2, byte_order="big"),
                      {'description': 'Test 0 - 65535 number, big-endian'})
        short = (IntegerBlock(length=2, is_signed=True),
                 {'description': 'Test -32768 - 32767 number'})
        required_int = (IntegerBlock(length=1, required_value=42),
                        {'description': 'Test required number'})
        # lookup string length
        var_str_length = (IntegerBlock(length=1),
                          {'description': 'Variable string length',
                           'programmatic_value': lambda ctx: len(ctx.data('var_str'))})
        # TODO Should automatically determine min_length, max_length
        var_str = (UTF8Block(length=lambda ctx: ctx.data('var_str_length')),
                   {'description': 'Test text field with variable length'})

        # TODO nested compound block
        # TODO array with fixed length
        # TODO array with lookup length
        next_block_type = (IntegerBlock(length=1),
                           {'programmatic_value': lambda ctx: len(ctx.data('delegate_block/data')) if isinstance(
                               ctx.data('delegate_block/data'), str) else 0})
        delegate_block = (DelegateBlock(possible_blocks=[IntegerBlock(length=4, is_signed=True),
                                                         UTF8Block(length=lambda ctx: ctx.data('next_block_type'))],
                                        choice_index=lambda ctx, **_: 1 if ctx.data('next_block_type') > 0 else 0),
                          {'description': 'Block, which can be either string, or signed integer'})
        # TODO array with delegated compound blocks
        # TODO block with offsets in the heap, heap block
