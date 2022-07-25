import unittest

from resources.eac.fields.numbers import Nfs1Angle14, Nfs1Angle8


class TestEacFields(unittest.TestCase):

    def test_angle_14_should_have_correct_rounding(self):
        field = Nfs1Angle14()
        raw = field.from_raw_value(bytes([92, 63]))
        serialized = field.to_raw_value(raw)
        self.assertListEqual(list(serialized), [92, 63])

    def test_angle_8_should_have_correct_rounding(self):
        field = Nfs1Angle8()
        raw = field.from_raw_value(bytes([11]))
        serialized = field.to_raw_value(raw)
        self.assertListEqual(list(serialized), [11])
