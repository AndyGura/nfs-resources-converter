import unittest
from io import BytesIO

from library.context import ReadContext
from library.read_blocks import DeclarativeCompoundBlock, IntegerBlock, OptionalBlock, LengthPrefixedArrayBlock


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

        from library.read_blocks.smart_fields import DelegateBlock
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
