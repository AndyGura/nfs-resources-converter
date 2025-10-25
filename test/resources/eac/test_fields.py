import unittest
from io import BytesIO

from library.context import ReadContext
from resources.eac.fields.colors import Color24BitDosBlock
from resources.eac.fields.numbers import Nfs1Angle14, Nfs1Angle8


class TestEacFields(unittest.TestCase):

    def test_angle_14_should_have_correct_rounding(self):
        field = Nfs1Angle14()
        raw = field.unpack(ReadContext(BytesIO(bytes([92, 63]))))
        serialized = field.pack(raw)
        self.assertListEqual(list(serialized), [92, 63])

    def test_angle_8_should_have_correct_rounding(self):
        field = Nfs1Angle8()
        raw = field.unpack(ReadContext(BytesIO(bytes([11]))))
        serialized = field.pack(raw)
        self.assertListEqual(list(serialized), [11])

    def test_color_24bit_dos_should_be_translated_correctly(self):
        field = Color24BitDosBlock()
        color = field.unpack(ReadContext(BytesIO(bytes([0b0010_1010, 0b0001_0100, 0b0011_1011]))))
        self.assertEqual(color, 0b10101000_01010000_11101100_11111111)

    def test_color_24bit_dos_should_be_saved_correctly(self):
        field = Color24BitDosBlock()
        color = 0b11101010_01010000_10101101_11111111
        serialized = field.pack(color)
        self.assertListEqual(list(serialized), [0b0011_1010, 0b0001_0100, 0b0010_1011])
