import unittest
from io import BytesIO

from library.context import ReadContext
from library.exceptions import DataIntegrityException
from library.read_blocks.misc.value_validators import Eq
from library.read_blocks.strings import UTF8Block


class TestStrings(unittest.TestCase):

    def test_utf8_unpack(self):
        field = UTF8Block(length=4)
        val = field.unpack(ReadContext(BytesIO(bytes([84, 101, 120, 116]))))
        self.assertEqual(val, "Text")

    def test_utf8_pack(self):
        field = UTF8Block(length=4)
        data = field.pack("Text")
        self.assertEqual(data, bytes([84, 101, 120, 116]))

    def test_utf8_value_validator(self):
        field = UTF8Block(length=5, value_validator=Eq("Asdfg"))
        field.unpack(ReadContext(BytesIO(bytes([65, 115, 100, 102, 103]))))
        with self.assertRaises(DataIntegrityException):
            field.unpack(ReadContext(BytesIO(bytes([84, 101, 120, 116, 83]))))

    def test_estimate_packed_size_not_static(self):
        field = UTF8Block(length=lambda ctx: 5)
        self.assertEqual(field.estimate_packed_size('foo'), 3)

    def test_estimate_packed_size_static(self):
        field = UTF8Block(length=4)
        size = field.estimate_packed_size("Te")
        self.assertEqual(size, 4)

    def test_estimate_packed_size_static_tuple(self):
        field = UTF8Block(length=(4, 'static length'))
        size = field.estimate_packed_size("Te")
        self.assertEqual(size, 4)

    def test_utf8_null_trailing_unpack(self):
        field = UTF8Block(length=4)
        val = field.unpack(ReadContext(BytesIO(bytes([84, 101, 0, 0]))))
        self.assertEqual(val, "Te")

    def test_utf8_null_trailing_pack(self):
        field = UTF8Block(length=4)
        data = field.pack("Te")
        self.assertEqual(data, bytes([84, 101, 0, 0]))

    def test_size_doc_str(self):
        field = UTF8Block(length=4)
        self.assertEqual(field.size_doc_str, "4")
        field = UTF8Block(length=(5, "5 chars"))
        self.assertEqual(field.size_doc_str, "5 chars")
        field = UTF8Block(length=lambda ctx: 10)
        self.assertEqual(field.size_doc_str, "10")

    def test_null_terminated_size_doc_str(self):
        from library.read_blocks.strings import NullTerminatedUTF8Block
        field = NullTerminatedUTF8Block(length=None)
        self.assertEqual(field.size_doc_str, "1..?")
