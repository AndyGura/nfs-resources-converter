import unittest
from io import BytesIO

from library.context import ReadContext
from library.exceptions import DataIntegrityException
from library.read_blocks.misc.value_validators import And, Eq, Gt, Gte, Lt, Lte
from library.read_blocks.numbers import IntegerBlock


class TestComparisonValidators(unittest.TestCase):
    def test_validate(self):
        self.assertTrue(Lt(60).validate(59))
        self.assertFalse(Lt(60).validate(60))
        self.assertTrue(Lte(60).validate(60))
        self.assertFalse(Lte(60).validate(61))
        self.assertTrue(Gt(-5).validate(-4))
        self.assertFalse(Gt(-5).validate(-5))
        self.assertTrue(Gte(-5).validate(-5))
        self.assertFalse(Gte(-5).validate(-6))

    def test_new_data_is_valid(self):
        for v in [Lt(60), Lt(0), Lt(-3), Lte(60), Lte(-3), Gt(-5), Gt(0), Gt(7), Gte(-5), Gte(7)]:
            self.assertTrue(v.validate(v.new_data()), str(v))
        self.assertEqual(Lte(60).new_data(), 0)
        self.assertEqual(Gte(7).new_data(), 7)

    def test_schema(self):
        self.assertEqual(Lt(1).schema(), {'type': 'lt', 'value': 1})
        self.assertEqual(Lte(2).schema(), {'type': 'lte', 'value': 2})
        self.assertEqual(Gt(3).schema(), {'type': 'gt', 'value': 3})
        self.assertEqual(Gte(4).schema(), {'type': 'gte', 'value': 4})

    def test_str(self):
        self.assertEqual(str(Lte(60)), 'Always <= 60')
        self.assertEqual(str(Gt(0)), 'Always > 0')


class TestAndValidator(unittest.TestCase):
    def test_validate(self):
        v = And(Gte(10), Lte(60))
        self.assertTrue(v.validate(10))
        self.assertTrue(v.validate(60))
        self.assertFalse(v.validate(9))
        self.assertFalse(v.validate(61))

    def test_new_data(self):
        self.assertEqual(And(Lte(60), Gte(0)).new_data(), 0)
        self.assertEqual(And(Lte(60), Gte(10)).new_data(), 10)
        with self.assertRaises(ValueError):
            And(Lte(5), Gte(10)).new_data()

    def test_schema(self):
        self.assertEqual(
            And(Gte(0), Lte(60)).schema(),
            {'type': 'and', 'validators': [{'type': 'gte', 'value': 0}, {'type': 'lte', 'value': 60}]},
        )

    def test_str(self):
        self.assertEqual(str(And(Gte(0), Lte(60))), 'Always >= 0 and <= 60')
        self.assertEqual(str(And(Gte(0), Eq(3))), '(Always >= 0) and (Always == 0x3)')

    def test_on_block(self):
        field = IntegerBlock(length=1, value_validator=And(Gte(10), Lte(60)))
        self.assertEqual(field.unpack(ReadContext(BytesIO(bytes([60])))), 60)
        with self.assertRaises(DataIntegrityException):
            field.unpack(ReadContext(BytesIO(bytes([61]))))
        self.assertEqual(field.new_data(), 10)
        self.assertIn('Always >= 10 and <= 60', field.schema['block_description'])
