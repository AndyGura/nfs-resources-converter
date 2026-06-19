import unittest
from library.read_blocks.basic import BytesBlock

class TestBasicBlocks(unittest.TestCase):

    def test_bytes_block_size_doc_str(self):
        # Static length
        field = BytesBlock(length=10)
        self.assertEqual(field.size_doc_str, "10")
        
        # Callable length
        field = BytesBlock(length=lambda ctx: 5)
        self.assertEqual(field.size_doc_str, "5")
        
        # Tuple length (doc override)
        field = BytesBlock(length=(lambda ctx: 5, "custom length"))
        self.assertEqual(field.size_doc_str, "custom length")
