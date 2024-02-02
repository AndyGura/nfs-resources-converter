import unittest
from io import BytesIO

from library.exceptions import DataIntegrityException
from library.read_blocks.strings import UTF8Block


class TestStrings(unittest.TestCase):

    def test_utf8_unpack(self):
        field = UTF8Block(length=4)
        val = field.unpack(BytesIO(bytes([84, 101, 120, 116])))
        self.assertEqual(val, "Text")

    def test_utf8_pack(self):
        field = UTF8Block(length=4)
        data = field.pack("Text")
        self.assertEqual(data, bytes([84, 101, 120, 116]))

    def test_utf8_required_value(self):
        field = UTF8Block(length=5, required_value="Asdfg")
        field.unpack(BytesIO(bytes([65, 115, 100, 102, 103])))
        with self.assertRaises(DataIntegrityException):
            field.unpack(BytesIO(bytes([84, 101, 120, 116, 83])))

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
        val = field.unpack(BytesIO(bytes([84, 101, 0, 0])))
        self.assertEqual(val, "Te")

    def test_utf8_null_trailing_pack(self):
        field = UTF8Block(length=4)
        data = field.pack("Te")
        self.assertEqual(data, bytes([84, 101, 0, 0]))
