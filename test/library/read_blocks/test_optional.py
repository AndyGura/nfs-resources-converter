import unittest
from io import BytesIO

from library.context import ReadContext, WriteContext
from library.read_blocks import (DeclarativeCompoundBlock, IntegerBlock, OptionalBlock, TrailingOptionalBlock,
                                 LengthPrefixedArrayBlock)


class OptionalTestBlock(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        has_optional = IntegerBlock(length=1)
        optional_field = OptionalBlock(
            child=IntegerBlock(length=2),
            criteria=lambda ctx: ctx.data('has_optional') == 1,
            default_value=0
        )
        marker = IntegerBlock(length=1)


class TestOptional(unittest.TestCase):

    def test_read_presented(self):
        block = OptionalTestBlock()
        # has_optional = 1, optional_field = 0x1234 (4660), marker = 0xFF (255)
        # 0x3412 for little-endian 4660
        data = bytes([1, 0x34, 0x12, 0xFF])
        res = block.unpack(ReadContext(BytesIO(data)))
        self.assertEqual(res['has_optional'], 1)
        self.assertEqual(res['optional_field'], 4660)
        self.assertEqual(res['marker'], 255)

    def test_read_skipped(self):
        block = OptionalTestBlock()
        # has_optional = 0, optional_field is skipped, marker = 0xFF (255)
        data = bytes([0, 0xFF])
        res = block.unpack(ReadContext(BytesIO(data)))
        self.assertEqual(res['has_optional'], 0)
        self.assertEqual(res['optional_field'], 0)  # default value
        self.assertEqual(res['marker'], 255)

    def test_write_presented(self):
        block = OptionalTestBlock()
        data = {
            'has_optional': 1,
            'optional_field': 4660,
            'marker': 255
        }
        packed = block.pack(data)
        self.assertEqual(packed, bytes([1, 0x34, 0x12, 0xFF]))

    def test_write_skipped(self):
        block = OptionalTestBlock()
        data = {
            'has_optional': 0,
            'optional_field': 4660,  # should be ignored
            'marker': 255
        }
        packed = block.pack(data)
        self.assertEqual(packed, bytes([0, 0xFF]))

    def test_estimate_size(self):
        block = OptionalTestBlock()
        data_presented = {'has_optional': 1, 'optional_field': 4660, 'marker': 255}
        self.assertEqual(block.estimate_packed_size(data_presented), 1 + 2 + 1)

        data_skipped = {'has_optional': 0, 'optional_field': 4660, 'marker': 255}
        self.assertEqual(block.estimate_packed_size(data_skipped), 1 + 0 + 1)

    def test_size_doc_str(self):
        opt = OptionalBlock(child=IntegerBlock(length=2), criteria=lambda ctx: True)
        self.assertEqual(opt.size_doc_str, '0..2')

        from library.read_blocks.delegates import DelegateBlock
        opt2 = OptionalBlock(child=DelegateBlock(possible_blocks=[IntegerBlock(length=2), IntegerBlock(length=4)]),
                             criteria=lambda ctx: True)
        self.assertEqual(opt2.size_doc_str, '0..4')

        from library.read_blocks.compound import CompoundBlock
        opt2 = OptionalBlock(child=CompoundBlock(fields=[
            ('a', IntegerBlock(length=4), {}),
            ('b', OptionalBlock(child=IntegerBlock(length=4), criteria=None), {})
        ]), criteria=lambda ctx: True)
        self.assertEqual(opt2.size_doc_str, '0..8')

    def test_schema(self):
        opt = OptionalBlock(child=IntegerBlock(length=2), criteria=lambda ctx: ctx.data('has_optional') == 1)
        schema = opt.schema
        self.assertTrue(schema['is_optional'])
        self.assertEqual(schema['block_class_mro'], 'IntegerBlock__DataBlock')
        # Check inlined child properties
        self.assertEqual(schema['block_description'], '2-bytes unsigned integer (little endian)')
        self.assertEqual(schema['criteria'], 'has_optional == 1')

    def test_schema_custom_label(self):
        opt = OptionalBlock(
            child=IntegerBlock(length=2),
            criteria=(lambda ctx: ctx.data('has_optional') == 1, "has_optional is set")
        )
        schema = opt.schema
        self.assertEqual(schema['criteria'], 'has_optional is set')

    def test_should_automatically_have_default_value(self):
        field = OptionalBlock(
            child=LengthPrefixedArrayBlock(length_block=IntegerBlock(length=1), child=IntegerBlock(length=1)),
            criteria=lambda ctx: False
        )
        self.assertEqual(field.new_data(), [])

    def test_get_child_block_with_data(self):
        class OptionalTestBlock(DeclarativeCompoundBlock):
            class Fields(DeclarativeCompoundBlock.Fields):
                has_optional = IntegerBlock(length=1)
                # should use [] as default value automatically here
                optional_field = OptionalBlock(
                    child=LengthPrefixedArrayBlock(length_block=IntegerBlock(length=1), child=IntegerBlock(length=1)),
                    criteria=lambda ctx: ctx.data('has_optional') == 1
                )
                marker = IntegerBlock(length=1)

        block = OptionalTestBlock()

        data = bytes([1, 2, 0x34, 0x12, 0xFF])
        res = block.unpack(ReadContext(BytesIO(data)))
        (ob, od) = block.get_child_block_with_data(res, 'optional_field')
        self.assertEqual(od, [0x34, 0x12])
        self.assertEqual(ob.get_child_block_with_data(od, '1')[1], 0x12)

        data = bytes([0, 0xFF])
        res = block.unpack(ReadContext(BytesIO(data)))
        (ob, od) = block.get_child_block_with_data(res, 'optional_field')
        self.assertEqual(od, [])


class TrailingOptionalTestBlock(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        marker = IntegerBlock(length=1)
        trailing_field = TrailingOptionalBlock(child=IntegerBlock(length=2))


def _looks_like_marker_byte(ctx, expected: int) -> bool:
    # peek at the next byte without consuming it - the read must be left untouched either way
    from io import SEEK_CUR
    peeked = ctx.buffer.read(1)
    ctx.buffer.seek(-len(peeked), SEEK_CUR)
    return len(peeked) == 1 and peeked[0] == expected


class SniffingTrailingOptionalTestBlock(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        marker = IntegerBlock(length=1)
        # present only if the very next byte is the chunk's own signature - the child's size is
        # irrelevant to that decision, unlike a plain "N bytes remaining" check
        trailing_field = TrailingOptionalBlock(
            child=IntegerBlock(length=2),
            criteria=(lambda ctx: _looks_like_marker_byte(ctx, 0xAA), 'next byte looks like 0xAA chunk')
        )


class TestTrailingOptional(unittest.TestCase):

    def test_read_presented(self):
        block = TrailingOptionalTestBlock()
        # marker, then 2 trailing bytes worth of space
        data = bytes([0xFF, 0x34, 0x12])
        ctx = ReadContext(BytesIO(data))
        res = block.unpack(ctx, read_bytes_amount=len(data))
        self.assertEqual(res['marker'], 255)
        self.assertEqual(res['trailing_field'], 4660)

    def test_read_absent_no_space_left(self):
        block = TrailingOptionalTestBlock()
        data = bytes([0xFF])  # nothing left after the marker
        ctx = ReadContext(BytesIO(data))
        res = block.unpack(ctx, read_bytes_amount=len(data))
        self.assertEqual(res['marker'], 255)
        self.assertIsNone(res['trailing_field'])

    def test_write_presented(self):
        block = TrailingOptionalTestBlock()
        data = {'marker': 255, 'trailing_field': 4660}
        self.assertEqual(block.pack(data), bytes([0xFF, 0x34, 0x12]))

    def test_write_absent_writes_nothing(self):
        block = TrailingOptionalTestBlock()
        data = {'marker': 255, 'trailing_field': None}
        self.assertEqual(block.pack(data), bytes([0xFF]))

    def test_write_does_not_depend_on_read_bytes_remaining(self):
        # WriteContext has no notion of "space available" - the field is never asked to
        # recompute its own presence while writing, only the value's None-ness is consulted.
        field = TrailingOptionalBlock(child=IntegerBlock(length=2))
        wctx = WriteContext()
        self.assertFalse(hasattr(wctx, 'read_bytes_remaining'))
        self.assertEqual(field.pack(4660, wctx), bytes([0x34, 0x12]))
        self.assertEqual(field.pack(None, wctx), b'')

    def test_round_trip_preserves_absence(self):
        # an unchanged file with no trailing data must not gain any on write
        block = TrailingOptionalTestBlock()
        data = bytes([0xFF])
        ctx = ReadContext(BytesIO(data))
        res = block.unpack(ctx, read_bytes_amount=len(data))
        self.assertEqual(block.pack(res), data)

    def test_custom_criteria_can_peek_and_leaves_buffer_untouched(self):
        block = SniffingTrailingOptionalTestBlock()
        # signature byte present -> field is read; the peek must not have consumed it, so the
        # child (which starts reading from the same position) sees it as its own first byte
        data = bytes([0xFF, 0xAA, 0x34])
        ctx = ReadContext(BytesIO(data))
        res = block.unpack(ctx, read_bytes_amount=len(data))
        self.assertEqual(res['trailing_field'], int.from_bytes(bytes([0xAA, 0x34]), 'little'))

    def test_custom_criteria_absent_when_signature_does_not_match(self):
        block = SniffingTrailingOptionalTestBlock()
        # next byte isn't the expected signature -> field is treated as absent, buffer untouched
        # for whatever comes after (there's nothing here, but the peek must not have consumed it)
        data = bytes([0xFF, 0xBB])
        ctx = ReadContext(BytesIO(data))
        res = block.unpack(ctx, read_bytes_amount=len(data))
        self.assertIsNone(res['trailing_field'])

    def test_two_consecutive_trailing_optional_blocks(self):
        # models e.g. bitmap mipmaps followed by an optional palette chunk: each of two
        # consecutive fields decides its own presence independently, in a known order
        class TwoChunksTestBlock(DeclarativeCompoundBlock):
            class Fields(DeclarativeCompoundBlock.Fields):
                chunk_a = TrailingOptionalBlock(
                    child=IntegerBlock(length=1),
                    criteria=(lambda ctx: _looks_like_marker_byte(ctx, 0xAA), 'next byte is 0xAA'))
                chunk_b = TrailingOptionalBlock(
                    child=IntegerBlock(length=1),
                    criteria=(lambda ctx: _looks_like_marker_byte(ctx, 0xBB), 'next byte is 0xBB'))

        block = TwoChunksTestBlock()

        both_present = bytes([0xAA, 0xBB])
        ctx = ReadContext(BytesIO(both_present))
        res = block.unpack(ctx, read_bytes_amount=len(both_present))
        self.assertEqual(res, {'chunk_a': 0xAA, 'chunk_b': 0xBB})
        self.assertEqual(block.pack(res), both_present)

        only_b_present = bytes([0xBB])
        ctx = ReadContext(BytesIO(only_b_present))
        res = block.unpack(ctx, read_bytes_amount=len(only_b_present))
        self.assertEqual(res, {'chunk_a': None, 'chunk_b': 0xBB})
        self.assertEqual(block.pack(res), only_b_present)

        neither_present = bytes([])
        ctx = ReadContext(BytesIO(neither_present))
        res = block.unpack(ctx, read_bytes_amount=len(neither_present))
        self.assertEqual(res, {'chunk_a': None, 'chunk_b': None})
        self.assertEqual(block.pack(res), neither_present)

    def test_estimate_size(self):
        field = TrailingOptionalBlock(child=IntegerBlock(length=2))
        self.assertEqual(field.estimate_packed_size(4660), 2)
        self.assertEqual(field.estimate_packed_size(None), 0)

    def test_new_data_is_absent_by_default(self):
        field = TrailingOptionalBlock(child=IntegerBlock(length=2))
        self.assertIsNone(field.new_data())

    def test_default_value_kwarg_is_ignored(self):
        # absence must always read back as None here, never a fabricated default
        field = TrailingOptionalBlock(child=IntegerBlock(length=2), default_value=999)
        self.assertIsNone(field.new_data())

    def test_size_doc_str(self):
        field = TrailingOptionalBlock(child=IntegerBlock(length=2))
        self.assertEqual(field.size_doc_str, '0..2')

    def test_schema(self):
        field = TrailingOptionalBlock(child=IntegerBlock(length=2))
        schema = field.schema
        self.assertTrue(schema['is_optional'])
        self.assertEqual(schema['criteria'], 'at least 1 byte remaining')
        # unlike OptionalBlock, this gets its own identity in the mro (a dedicated GUI component
        # renders the presence toggle) with the child's schema nested, not spread in
        self.assertEqual(schema['block_class_mro'], 'TrailingOptionalBlock__OptionalBlock__DataBlock')
        self.assertEqual(schema['child_schema']['block_class_mro'], 'IntegerBlock__DataBlock')

    def test_schema_custom_criteria_label(self):
        field = TrailingOptionalBlock(
            child=IntegerBlock(length=2),
            criteria=(lambda ctx: ctx.read_bytes_remaining >= 2, 'room for a checksum')
        )
        self.assertEqual(field.schema['criteria'], 'room for a checksum')
