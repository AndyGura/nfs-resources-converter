import unittest
from io import BytesIO

from library.context import ReadContext
from library.read_blocks import ArrayBlock, DeclarativeCompoundBlock, IntegerBlock, UTF8Block, CompoundBlock


class TestCompound(unittest.TestCase):

    def test_unpack(self):
        field = CompoundBlock(fields=[
            ('a', IntegerBlock(length=1), {}),
            ('b', IntegerBlock(length=1), {}),
        ])
        val = field.unpack(ReadContext(BytesIO(bytes([92, 129]))))
        self.assertDictEqual(val, {'a': 92, 'b': 129})

    def test_pack(self):
        field = CompoundBlock(fields=[
            ('a', IntegerBlock(length=1), {}),
            ('b', IntegerBlock(length=1), {}),
        ])
        data = field.pack({'a': 92, 'b': 129})
        self.assertEqual(data, bytes([92, 129]))

    def test_get_child_block_with_data(self):
        child_block = IntegerBlock(length=1)
        field = CompoundBlock(fields=[
            ('a', IntegerBlock(length=2), {}),
            ('b', child_block, {}),
        ])
        block, data = field.get_child_block_with_data({'a': 123, 'b': 456}, 'b')
        self.assertEqual(block, child_block)
        self.assertEqual(data, 456)

    def test_estimate_packed_size(self):
        field = CompoundBlock(fields=[
            ('a', IntegerBlock(length=2), {}),
            ('b', UTF8Block(length=lambda ctx: exec('raise Exception()')), {}),
        ])
        self.assertEqual(field.estimate_packed_size({'a': 123, 'b': '123qwerty'}), 11)

    def test_offset_to_child_when_packed(self):
        field = CompoundBlock(fields=[
            ('foo', UTF8Block(length=lambda ctx: exec('raise Exception()')), {}),
            ('bar', IntegerBlock(length=2), {}),
        ])
        self.assertEqual(field.offset_to_child_when_packed({'foo': 'test_str', 'bar': 2}, 'bar'), 8)


class SimpleBlock(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        a = IntegerBlock(length=1)
        b = IntegerBlock(length=1)


class BindingBlock(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        header = IntegerBlock(length=1, required_value=2), {'description': "Some header"}
        len = (IntegerBlock(length=1),
               {'description': "A length of `val` array",
                'programmatic_value': lambda ctx: len(ctx.data('val'))})
        val = ArrayBlock(child=IntegerBlock(length=1), length=lambda ctx: ctx.data('len'))


class BindingBlockWithDoc(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        header = IntegerBlock(length=1, required_value=2), {'description': "Some header"}
        len = (IntegerBlock(length=1),
               {'description': "A length of `val` array",
                'programmatic_value': lambda ctx: len(ctx.data('val'))})
        val = ArrayBlock(child=IntegerBlock(length=1), length=lambda ctx: ctx.data('len'))


class TestDeclarativeCompound(unittest.TestCase):

    def test_unpack(self):
        field = SimpleBlock()
        val = field.unpack(ReadContext(BytesIO(bytes([92, 129]))))
        self.assertDictEqual(val, {'a': 92, 'b': 129})

    def test_pack(self):
        field = SimpleBlock()
        data = field.pack({'a': 92, 'b': 129})
        self.assertEqual(data, bytes([92, 129]))

    def test_simple_value_binding_unpack(self):
        field = BindingBlock()
        val = field.unpack(ReadContext(BytesIO(bytes([2, 3, 129, 145, 12, 9]))))
        self.assertDictEqual(val, {'header': 2, 'len': 3, 'val': [129, 145, 12]})

    def test_simple_value_binding_with_doc_pack(self):
        field = BindingBlockWithDoc()
        data = field.pack({'header': 2, 'len': 4, 'val': [129, 145, 12, 14]})
        self.assertEqual(data, bytes([2, 4, 129, 145, 12, 14]))

    def test_simple_value_binding_with_doc_unpack(self):
        field = BindingBlockWithDoc()
        val = field.unpack(ReadContext(BytesIO(bytes([2, 3, 129, 145, 12, 9]))))
        self.assertDictEqual(val, {'header': 2, 'len': 3, 'val': [129, 145, 12]})

    def test_simple_value_binding_pack(self):
        field = BindingBlock()
        data = field.pack({'header': 2, 'len': 4, 'val': [129, 145, 12, 14]})
        self.assertEqual(data, bytes([2, 4, 129, 145, 12, 14]))

    def test_simple_value_binding_pack_with_skipped_programmatic_field(self):
        field = BindingBlock()
        data = field.pack({'header': 2, 'val': [129, 145, 12, 14]})
        self.assertEqual(data, bytes([2, 4, 129, 145, 12, 14]))

    def test_simple_value_binding_pack_with_wrong_programmatic_field(self):
        field = BindingBlock()
        data = field.pack({'header': 2, 'len': 229, 'val': [129, 145, 12, 14]})
        self.assertEqual(data, bytes([2, 4, 129, 145, 12, 14]))

    def test_schema(self):
        field = BindingBlockWithDoc()
        self.maxDiff = None
        self.assertDictEqual(
            field.schema,
            {
                'block_class_mro': 'BindingBlockWithDoc__DeclarativeCompoundBlock__CompoundBlock__DataBlockWithChildren__DataBlock',
                'block_description': '',
                'serializable_to_disc': False,
                'inline_description': False,
                'fields': [
                    {
                        'name': 'header',
                        'schema': {
                            'block_class_mro': 'IntegerBlock__DataBlock',
                            'block_description': '1-byte unsigned integer. Always == 0x2',
                            'required_value': 2,
                            'serializable_to_disc': False,
                            'min_value': 0,
                            'max_value': 255,
                            'value_interval': 1,
                        },
                        'is_programmatic': False,
                        'is_unknown': False,
                        'usage': 'everywhere',
                        'description': "Some header",
                    },
                    {
                        'name': 'len',
                        'schema': {
                            'block_class_mro': 'IntegerBlock__DataBlock',
                            'block_description': '1-byte unsigned integer',
                            'serializable_to_disc': False,
                            'min_value': 0,
                            'max_value': 255,
                            'value_interval': 1,
                        },
                        'is_programmatic': True,
                        'is_unknown': False,
                        'usage': 'everywhere',
                        'description': "A length of `val` array"
                    },
                    {
                        'name': 'val',
                        'schema': {
                            'block_class_mro': 'ArrayBlock__DataBlockWithChildren__DataBlock',
                            'block_description': 'Array of `len` items',
                            'serializable_to_disc': False,
                            'child_schema': {
                                'block_class_mro': 'IntegerBlock__DataBlock',
                                'block_description': '1-byte unsigned integer',
                                'serializable_to_disc': False,
                                'min_value': 0,
                                'max_value': 255,
                                'value_interval': 1,
                            }
                        },
                        'is_programmatic': False,
                        'is_unknown': False,
                        'usage': 'everywhere',
                        'description': ""
                    }
                ]
            })
