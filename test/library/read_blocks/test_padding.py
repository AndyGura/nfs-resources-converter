import unittest
from io import BytesIO
from library.context import ReadContext
from library.read_blocks import DeclarativeCompoundBlock, IntegerBlock, Padding

class TestPadding(unittest.TestCase):

    def test_padding_global_offset(self):
        class GlobalPaddingBlock(DeclarativeCompoundBlock):
            class Fields(DeclarativeCompoundBlock.Fields):
                header = IntegerBlock(length=4)
                # Pad to absolute offset 12
                padding = Padding(to=12, is_global=True)
                data = IntegerBlock(length=4)

        # Buffer: 4 bytes (header) + 8 bytes (padding) + 4 bytes (data) = 16 bytes
        # Offset 0-4: header
        # Offset 4-12: padding
        # Offset 12-16: data
        buf = BytesIO(b'\x01\x00\x00\x00' + b'\x00' * 8 + b'\x02\x00\x00\x00')
        ctx = ReadContext(buf)
        block = GlobalPaddingBlock()
        unpacked = block.unpack(ctx)

        self.assertEqual(unpacked['header'], 1)
        self.assertEqual(len(unpacked['padding']), 8)
        self.assertEqual(unpacked['data'], 2)
        self.assertEqual(buf.tell(), 16)

    def test_padding_local_offset(self):
        class LocalPaddingInner(DeclarativeCompoundBlock):
            class Fields(DeclarativeCompoundBlock.Fields):
                header = IntegerBlock(length=2)
                # Pad to local offset 6
                padding = Padding(to=6, is_global=False)
                data = IntegerBlock(length=2)

        class LocalPaddingOuter(DeclarativeCompoundBlock):
            class Fields(DeclarativeCompoundBlock.Fields):
                outer_header = IntegerBlock(length=4)
                inner = LocalPaddingInner()

        # Buffer: 
        # 0-4: outer_header
        # 4-6: inner.header (local 0-2)
        # 6-10: inner.padding (local 2-6)
        # 10-12: inner.data (local 6-8)
        buf = BytesIO(b'\xff\xff\xff\xff' + b'\x01\x00' + b'\x00' * 4 + b'\x02\x00')
        ctx = ReadContext(buf)
        block = LocalPaddingOuter()
        unpacked = block.unpack(ctx)

        self.assertEqual(unpacked['outer_header'], 0xffffffff)
        self.assertEqual(unpacked['inner']['header'], 1)
        self.assertEqual(len(unpacked['inner']['padding']), 4)
        self.assertEqual(unpacked['inner']['data'], 2)
        self.assertEqual(buf.tell(), 12)

    def test_padding_with_lambda_and_description(self):
        class LambdaPaddingBlock(DeclarativeCompoundBlock):
            class Fields(DeclarativeCompoundBlock.Fields):
                target = IntegerBlock(length=1)
                padding = Padding(to=(lambda ctx: ctx.data('target'), 'target_value'), is_global=True)
                data = IntegerBlock(length=1)

        # Buffer:
        # Offset 0: target = 5
        # Offset 1-5: padding (4 bytes)
        # Offset 5: data = 10
        buf = BytesIO(b'\x05' + b'\x00' * 4 + b'\x0a')
        ctx = ReadContext(buf)
        block = LambdaPaddingBlock()
        unpacked = block.unpack(ctx)

        self.assertEqual(unpacked['target'], 5)
        self.assertEqual(len(unpacked['padding']), 4)
        self.assertEqual(unpacked['data'], 10)
        self.assertEqual(buf.tell(), 6)

    def test_padding_schema(self):
        padding = Padding(to=10)
        schema = padding.schema
        self.assertEqual(schema['block_description'], 'Padding bytes')
        self.assertIn('up to offset 10', padding.size_doc_str)

    def test_padding_write(self):
        # Padding should not write anything as it's a "skip" block conceptually, 
        # but it inherits from BytesBlock which writes data.
        # Actually Padding is used for reading, but for writing it should 
        # probably be handled.
        padding = Padding(to=10)
        self.assertEqual(padding.write(b'\x00' * 5), b'\x00' * 5)

    def test_padding_negative_length_fails_by_default(self):
        class InvalidPaddingBlock(DeclarativeCompoundBlock):
            class Fields(DeclarativeCompoundBlock.Fields):
                header = IntegerBlock(length=10)
                # Offset is already 10, but we want to pad to 5
                padding = Padding(to=5)

        buf = BytesIO(b'\x00' * 10)
        ctx = ReadContext(buf)
        block = InvalidPaddingBlock()
        
        from library.exceptions import BlockDefinitionException
        with self.assertRaises(BlockDefinitionException):
            block.unpack(ctx)

    def test_padding_allow_negative_length(self):
        class NegativePaddingBlock(DeclarativeCompoundBlock):
            class Fields(DeclarativeCompoundBlock.Fields):
                header = IntegerBlock(length=10)
                # Offset is 10, seek back to 5
                padding = Padding(to=5, allow_negative_length=True)
                data = IntegerBlock(length=1)

        buf = BytesIO(b'0123456789A')
        ctx = ReadContext(buf)
        block = NegativePaddingBlock()
        unpacked = block.unpack(ctx)

        self.assertEqual(buf.tell(), 6) # 5 + 1
        self.assertEqual(unpacked['data'], ord('5'))
