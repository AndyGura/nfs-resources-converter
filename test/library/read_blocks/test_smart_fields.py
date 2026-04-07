import unittest

from library.read_blocks import CompoundBlock
from library.read_blocks.misc.optional import OptionalBlock
from library.read_blocks.numbers import IntegerBlock
from library.read_blocks.smart_fields import DelegateBlock

class TestSmartFields(unittest.TestCase):

    def test_delegate_block_size_doc_str(self):
        # same sizes
        field = DelegateBlock(possible_blocks=[
            IntegerBlock(length=2),
            IntegerBlock(length=2)
        ])
        self.assertEqual(field.size_doc_str, "2")

        # range of sizes
        field = DelegateBlock(possible_blocks=[
            IntegerBlock(length=2),
            IntegerBlock(length=4)
        ])
        self.assertEqual(field.size_doc_str, "2..4")

        # unknown sizes
        from library.read_blocks.strings import NullTerminatedUTF8Block
        field = DelegateBlock(possible_blocks=[
            IntegerBlock(length=2),
            NullTerminatedUTF8Block(length=None)
        ])
        self.assertEqual(field.size_doc_str, "1..?")

        field = DelegateBlock(possible_blocks=[
            # length 2
            IntegerBlock(length=2),
            # length 4..8
            CompoundBlock(fields=[
                ('a', IntegerBlock(length=4), {}),
                ('b', OptionalBlock(child=IntegerBlock(length=4), criteria=None), {})
            ])
        ])
        self.assertEqual(field.size_doc_str, '2..8')
