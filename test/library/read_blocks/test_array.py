import unittest
from io import BytesIO

from library.exceptions import DataIntegrityException
from library.read_blocks import UTF8Block
from library.read_blocks.array import ArrayBlock, LengthPrefixedArrayBlock, SubByteArrayBlock
from library.read_blocks.numbers import IntegerBlock


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

    def test_get_child_block_with_data(self):
        child_block = IntegerBlock(length=1)
        field = ArrayBlock(length=3, child=child_block)
        block, data = field.get_child_block_with_data([123, 456, 789], '1')
        self.assertEqual(block, child_block)
        self.assertEqual(data, 456)

    def test_estimate_packed_size(self):
        field = ArrayBlock(length=3, child=IntegerBlock(length=3))
        self.assertEqual(field.estimate_packed_size([1, 2, 3]), 9)

    def test_estimate_packed_size_variable_child_length(self):
        field = ArrayBlock(length=3, child=UTF8Block(length=lambda ctx: exec('raise Exception()')))
        self.assertEqual(field.estimate_packed_size(['abc', '0', 'qwerty']), 10)

    def test_offset_to_child_when_packed(self):
        field = ArrayBlock(length=3, child=UTF8Block(length=lambda ctx: exec('raise Exception()')))
        self.assertEqual(field.offset_to_child_when_packed(['abc', '0', 'qwerty'], '1'), 3)


class TestLengthPrefixedArray(unittest.TestCase):

    def test_array_unpack(self):
        field = LengthPrefixedArrayBlock(length_block=IntegerBlock(length=1), child=IntegerBlock(length=1))
        val = field.unpack(BytesIO(bytes([3, 92, 129, 13, 252])))
        self.assertListEqual(val, [92, 129, 13])

    def test_array_unpack_different_length_block(self):
        field = LengthPrefixedArrayBlock(length_block=IntegerBlock(length=4, byte_order='big'), child=IntegerBlock(length=1))
        self.assertListEqual(field.unpack(BytesIO(bytes([0, 0, 0, 2, 92, 129, 254]))), [92, 129])
        field = LengthPrefixedArrayBlock(length_block=IntegerBlock(length=4, byte_order='little'), child=IntegerBlock(length=1))
        self.assertListEqual(field.unpack(BytesIO(bytes([2, 0, 0, 0, 92, 129, 254]))), [92, 129])
        field = LengthPrefixedArrayBlock(length_block=IntegerBlock(length=3, byte_order='big'), child=IntegerBlock(length=1))
        self.assertListEqual(field.unpack(BytesIO(bytes([0, 0, 3, 92, 129, 254, 127]))), [92, 129, 254])

    def test_array_pack(self):
        field = LengthPrefixedArrayBlock(length_block=IntegerBlock(length=1), child=IntegerBlock(length=1))
        data = field.pack([92, 129, 13])
        self.assertEqual(data, bytes([3, 92, 129, 13]))

    def test_array_pack_different_length_block(self):
        field = LengthPrefixedArrayBlock(length_block=IntegerBlock(length=4, byte_order='big'), child=IntegerBlock(length=1))
        self.assertEqual(field.pack([92, 129]), bytes([0, 0, 0, 2, 92, 129]))
        field = LengthPrefixedArrayBlock(length_block=IntegerBlock(length=4, byte_order='little'), child=IntegerBlock(length=1))
        self.assertEqual(field.pack([92, 129]), bytes([2, 0, 0, 0, 92, 129]))
        field = LengthPrefixedArrayBlock(length_block=IntegerBlock(length=3, byte_order='big'), child=IntegerBlock(length=1))
        self.assertEqual(field.pack([92, 129, 13, 12, 15]), bytes([0, 0, 5, 92, 129, 13, 12, 15]))

    def test_array_required_value(self):
        field = LengthPrefixedArrayBlock(length_block=IntegerBlock(length=1), child=IntegerBlock(length=1), required_value=[10, 20, 30])
        field.unpack(BytesIO(bytes([3, 10, 20, 30])))
        with self.assertRaises(DataIntegrityException):
            field.unpack(BytesIO(bytes([3, 90, 12, 30])))

    def test_get_child_block_with_data(self):
        child_block = IntegerBlock(length=1)
        field = LengthPrefixedArrayBlock(length_block=IntegerBlock(length=1), child=child_block)
        block, data = field.get_child_block_with_data([123, 456, 789], '1')
        self.assertEqual(block, child_block)
        self.assertEqual(data, 456)

    def test_estimate_packed_size(self):
        field = LengthPrefixedArrayBlock(length_block=IntegerBlock(length=1), child=IntegerBlock(length=3))
        self.assertEqual(field.estimate_packed_size([1, 2, 3]), 10)
        field = LengthPrefixedArrayBlock(length_block=IntegerBlock(length=4), child=IntegerBlock(length=3))
        self.assertEqual(field.estimate_packed_size([1, 2, 3]), 13)

    def test_estimate_packed_size_variable_child_length(self):
        field = LengthPrefixedArrayBlock(length_block=IntegerBlock(length=1), child=UTF8Block(length=lambda ctx: exec('raise Exception()')))
        self.assertEqual(field.estimate_packed_size(['abc', '0', 'qwerty']), 11)

    def test_offset_to_child_when_packed(self):
        field = LengthPrefixedArrayBlock(length_block=IntegerBlock(length=1), child=UTF8Block(length=lambda ctx: exec('raise Exception()')))
        self.assertEqual(field.offset_to_child_when_packed(['abc', '0', 'qwerty'], '1'), 4)
        field = LengthPrefixedArrayBlock(length_block=IntegerBlock(length=4), child=UTF8Block(length=lambda ctx: exec('raise Exception()')))
        self.assertEqual(field.offset_to_child_when_packed(['abc', '0', 'qwerty'], '1'), 7)


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

    def test_get_child_block_with_data(self):
        field = SubByteArrayBlock(length=5, bits_per_value=5)
        block, data = field.get_child_block_with_data([29, 26, 13], '1')
        self.assertIsNone(block)
        self.assertEqual(data, 26)

    def test_estimate_packed_size(self):
        field = SubByteArrayBlock(length=5, bits_per_value=5)
        self.assertEqual(field.estimate_packed_size([1, 2, 3]), 2)
