import unittest
from io import BytesIO

from resources.eac.fields.numbers import Nfs1Angle14, Nfs1Angle8


class TestEacFields(unittest.TestCase):

    def test_angle_14_should_have_correct_rounding(self):
        field = Nfs1Angle14()
        raw = field.unpack(BytesIO(bytes([92, 63])))
        serialized = field.pack(raw)
        self.assertListEqual(list(serialized), [92, 63])

    def test_angle_8_should_have_correct_rounding(self):
        field = Nfs1Angle8()
        raw = field.unpack(BytesIO(bytes([11])))
        serialized = field.pack(raw)
        self.assertListEqual(list(serialized), [11])
