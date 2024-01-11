import unittest
from io import BytesIO

from library2.read_blocks.array import ArrayBlock
from library2.read_blocks.compound import CompoundBlock
from library2.read_blocks.numbers import IntegerBlock


class SimpleBlock(CompoundBlock):
    class Fields(CompoundBlock.Fields):
        a = IntegerBlock(length=1)
        b = IntegerBlock(length=1)


class BindingBlock(CompoundBlock):
    class Fields(CompoundBlock.Fields):
        header = IntegerBlock(length=1, required_value=2), {'description': "Some header"}
        len = (IntegerBlock(length=1),
               {'description': "A length of `val` array",
                'programmatic_value': lambda ctx: len(ctx.data('val'))})
        val = ArrayBlock(child=IntegerBlock(length=1), length=lambda ctx: ctx.data('len'))


class BindingBlockWithDoc(CompoundBlock):
    class Fields(CompoundBlock.Fields):
        header = IntegerBlock(length=1, required_value=2), {'description': "Some header"}
        len = (IntegerBlock(length=1),
               {'description': "A length of `val` array",
                'programmatic_value': lambda ctx: len(ctx.data('val'))})
        val = ArrayBlock(child=IntegerBlock(length=1), length=(lambda ctx: ctx.data('len'), "len"))


class TestCompound(unittest.TestCase):

    def test_compound_unpack(self):
        field = SimpleBlock()
        val = field.unpack(BytesIO(bytes([92, 129])))
        self.assertDictEqual(val, {'a': 92, 'b': 129})

    def test_compound_pack(self):
        field = SimpleBlock()
        data = field.pack({'a': 92, 'b': 129})
        self.assertEqual(data, bytes([92, 129]))

    def test_simple_value_binding_unpack(self):
        field = BindingBlock()
        val = field.unpack(BytesIO(bytes([2, 3, 129, 145, 12, 9])))
        self.assertDictEqual(val, {'header': 2, 'len': 3, 'val': [129, 145, 12]})

    def test_simple_value_binding_with_doc_pack(self):
        field = BindingBlockWithDoc()
        data = field.pack({'header': 2, 'len': 4, 'val': [129, 145, 12, 14]})
        self.assertEqual(data, bytes([2, 4, 129, 145, 12, 14]))

    def test_simple_value_binding_with_doc_unpack(self):
        field = BindingBlockWithDoc()
        val = field.unpack(BytesIO(bytes([2, 3, 129, 145, 12, 9])))
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
        self.assertDictEqual(
            field.schema,
            {
                'block_class_mro': 'BindingBlockWithDoc__CompoundBlock__DataBlock',
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
                        'is_unknown': False
                    },
                    {
                        'name': 'val',
                        'schema': {
                            'block_class_mro': 'ArrayBlock__DataBlock',
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
                        'is_unknown': False
                    }
                ]
            })
