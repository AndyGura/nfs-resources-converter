import unittest
from io import BytesIO

from library.helpers.exceptions import DataIntegrityException
from library2.read_blocks.array import ArrayBlock, SubByteArrayBlock
from library2.read_blocks.compound import CompoundBlock
from library2.read_blocks.numbers import IntegerBlock
from resources.eac.fields.numbers import Nfs1Angle14, Nfs1Angle8


class TestArray(unittest.TestCase):

    def test_array_unpack(self):
        field = ArrayBlock(length=3, child=IntegerBlock(length=1))
        val = field.unpack(BytesIO(bytes([92, 129, 13])))
        self.assertListEqual(val, [92, 129, 13])

    def test_array_pack(self):
        field = ArrayBlock(length=3, child=IntegerBlock(length=1))
        data = field.pack([92, 129, 13])
        self.assertEqual(data, bytes([92, 129, 13]))

    def test_array_required_value(self):
        field = ArrayBlock(length=3, child=IntegerBlock(length=1), required_value=[10, 20, 30])
        field.unpack(BytesIO(bytes([10, 20, 30])))
        with self.assertRaises(DataIntegrityException):
            field.unpack(BytesIO(bytes([90, 12, 30])))


class TestSubByteArray(unittest.TestCase):

    def test_subbyte_array_unpack(self):
        field = SubByteArrayBlock(length=4, bits_per_value=6)
        val = field.unpack(BytesIO(bytes([253, 253, 253])))
        self.assertListEqual(val, [63, 31, 55, 61])

    def test_subbyte_array_pack(self):
        field = SubByteArrayBlock(length=4, bits_per_value=6)
        data = field.pack([63, 31, 55, 61])
        self.assertEqual(data, bytes([253, 253, 253]))

    def test_subbyte_array_unpack_padding(self):
        field = SubByteArrayBlock(length=5, bits_per_value=5)
        val = field.unpack(BytesIO(bytes([255, 255, 255, 128])))
        self.assertListEqual(val, [31, 31, 31, 31, 31])

    def test_subbyte_array_pack_padding(self):
        field = SubByteArrayBlock(length=5, bits_per_value=5)
        data = field.pack([31, 31, 31, 31, 31])
        self.assertEqual(data, bytes([255, 255, 255, 128]))
