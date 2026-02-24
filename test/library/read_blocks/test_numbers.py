import unittest
from io import BytesIO

from library.context import ReadContext
from library.exceptions import DataIntegrityException
from library.read_blocks.misc.value_validators import Eq
from library.read_blocks.numbers import IntegerBlock


class TestByteNumber(unittest.TestCase):

    def test_unsigned_unpack(self):
        field = IntegerBlock(length=1)
        val = field.unpack(ReadContext(BytesIO(bytes([92]))))
        self.assertEqual(val, 92)
        val = field.unpack(ReadContext(BytesIO(bytes([253]))))
        self.assertEqual(val, 253)

    def test_unsigned_pack(self):
        field = IntegerBlock(length=1)
        data = field.pack(92)
        self.assertEqual(data, bytes([92]))
        data = field.pack(253)
        self.assertEqual(data, bytes([253]))
        with self.assertRaises(OverflowError):
            field.pack(-3)

    def test_unsigned_value_validator(self):
        field = IntegerBlock(length=1, value_validator=Eq(25))
        field.unpack(ReadContext(BytesIO(bytes([25]))))
        with self.assertRaises(DataIntegrityException):
            field.unpack(ReadContext(BytesIO(bytes([92]))))
        field = IntegerBlock(length=1, value_validator=Eq(253))
        field.unpack(ReadContext(BytesIO(bytes([253]))))
        with self.assertRaises(DataIntegrityException):
            field.unpack(ReadContext(BytesIO(bytes([180]))))

    def test_signed_unpack(self):
        field = IntegerBlock(length=1, is_signed=True)
        val = field.unpack(ReadContext(BytesIO(bytes([92]))))
        self.assertEqual(val, 92)
        val = field.unpack(ReadContext(BytesIO(bytes([253]))))
        self.assertEqual(val, -3)

    def test_signed_pack(self):
        field = IntegerBlock(length=1, is_signed=True)
        data = field.pack(92)
        self.assertEqual(data, bytes([92]))
        data = field.pack(-3)
        self.assertEqual(data, bytes([253]))
        with self.assertRaises(OverflowError):
            field.pack(253)

    def test_signed_value_validator(self):
        field = IntegerBlock(length=1, value_validator=Eq(-5), is_signed=True)
        field.unpack(ReadContext(BytesIO(bytes([251]))))
        with self.assertRaises(DataIntegrityException):
            field.unpack(ReadContext(BytesIO(bytes([252]))))
        field = IntegerBlock(length=1, value_validator=Eq(12), is_signed=True)
        field.unpack(ReadContext(BytesIO(bytes([12]))))
        with self.assertRaises(DataIntegrityException):
            field.unpack(ReadContext(BytesIO(bytes([244]))))


class TestShortNumber(unittest.TestCase):

    def test_le_unsigned_unpack(self):
        field = IntegerBlock(length=2)
        val = field.unpack(ReadContext(BytesIO(bytes([92, 0]))))
        self.assertEqual(val, 92)
        val = field.unpack(ReadContext(BytesIO(bytes([252, 253]))))
        self.assertEqual(val, 65020)

    def test_le_unsigned_pack(self):
        field = IntegerBlock(length=2)
        data = field.pack(92)
        self.assertEqual(data, bytes([92, 0]))
        data = field.pack(65020)
        self.assertEqual(data, bytes([252, 253]))
        with self.assertRaises(OverflowError):
            field.pack(-3)

    def test_le_unsigned_value_validator(self):
        field = IntegerBlock(length=2, value_validator=Eq(65020))
        field.unpack(ReadContext(BytesIO(bytes([252, 253]))))
        with self.assertRaises(DataIntegrityException):
            field.unpack(ReadContext(BytesIO(bytes([253, 252]))))
        field = IntegerBlock(length=2, value_validator=Eq(253))
        field.unpack(ReadContext(BytesIO(bytes([253, 0]))))
        with self.assertRaises(DataIntegrityException):
            field.unpack(ReadContext(BytesIO(bytes([180, 0]))))

    def test_le_signed_unpack(self):
        field = IntegerBlock(length=2, is_signed=True)
        val = field.unpack(ReadContext(BytesIO(bytes([92, 0]))))
        self.assertEqual(val, 92)
        val = field.unpack(ReadContext(BytesIO(bytes([253, 252]))))
        self.assertEqual(val, -771)

    def test_le_signed_pack(self):
        field = IntegerBlock(length=2, is_signed=True)
        data = field.pack(92)
        self.assertEqual(data, bytes([92, 0]))
        data = field.pack(-771)
        self.assertEqual(data, bytes([253, 252]))
        with self.assertRaises(OverflowError):
            field.pack(40000)

    def test_le_signed_value_validator(self):
        field = IntegerBlock(length=2, value_validator=Eq(-771), is_signed=True)
        field.unpack(ReadContext(BytesIO(bytes([253, 252]))))
        with self.assertRaises(DataIntegrityException):
            field.unpack(ReadContext(BytesIO(bytes([0, 251]))))
        field = IntegerBlock(length=2, value_validator=Eq(12), is_signed=True)
        field.unpack(ReadContext(BytesIO(bytes([12, 0]))))
        with self.assertRaises(DataIntegrityException):
            field.unpack(ReadContext(BytesIO(bytes([244, 1]))))

    def test_be_unsigned_unpack(self):
        field = IntegerBlock(length=2, byte_order="big")
        val = field.unpack(ReadContext(BytesIO(bytes([0, 92]))))
        self.assertEqual(val, 92)
        val = field.unpack(ReadContext(BytesIO(bytes([253, 252]))))
        self.assertEqual(val, 65020)

    def test_be_unsigned_pack(self):
        field = IntegerBlock(length=2, byte_order="big")
        data = field.pack(92)
        self.assertEqual(data, bytes([0, 92]))
        data = field.pack(65020)
        self.assertEqual(data, bytes([253, 252]))
        with self.assertRaises(OverflowError):
            field.pack(-3)

    def test_be_unsigned_value_validator(self):
        field = IntegerBlock(length=2, byte_order="big", value_validator=Eq(65020))
        field.unpack(ReadContext(BytesIO(bytes([253, 252]))))
        with self.assertRaises(DataIntegrityException):
            field.unpack(ReadContext(BytesIO(bytes([252, 253]))))
        field = IntegerBlock(length=2, byte_order="big", value_validator=Eq(253))
        field.unpack(ReadContext(BytesIO(bytes([0, 253]))))
        with self.assertRaises(DataIntegrityException):
            field.unpack(ReadContext(BytesIO(bytes([0, 180]))))

    def test_be_signed_unpack(self):
        field = IntegerBlock(length=2, byte_order="big", is_signed=True)
        val = field.unpack(ReadContext(BytesIO(bytes([0, 92]))))
        self.assertEqual(val, 92)
        val = field.unpack(ReadContext(BytesIO(bytes([252, 253]))))
        self.assertEqual(val, -771)

    def test_be_signed_pack(self):
        field = IntegerBlock(length=2, byte_order="big", is_signed=True)
        data = field.pack(92)
        self.assertEqual(data, bytes([0, 92]))
        data = field.pack(-771)
        self.assertEqual(data, bytes([252, 253]))
        with self.assertRaises(OverflowError):
            field.pack(40000)

    def test_be_signed_value_validator(self):
        field = IntegerBlock(length=2, byte_order="big", value_validator=Eq(-771), is_signed=True)
        field.unpack(ReadContext(BytesIO(bytes([252, 253]))))
        with self.assertRaises(DataIntegrityException):
            field.unpack(ReadContext(BytesIO(bytes([251, 0]))))
        field = IntegerBlock(length=2, byte_order="big", value_validator=Eq(12), is_signed=True)
        field.unpack(ReadContext(BytesIO(bytes([0, 12]))))
        with self.assertRaises(DataIntegrityException):
            field.unpack(ReadContext(BytesIO(bytes([1, 244]))))
