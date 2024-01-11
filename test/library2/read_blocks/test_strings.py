import unittest
from io import BytesIO

from library.helpers.exceptions import DataIntegrityException
from library2.read_blocks.strings import UTF8Block


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
