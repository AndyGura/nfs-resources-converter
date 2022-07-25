import unittest

from library import require_file


class TestTRISerializeDeserialize(unittest.TestCase):

    def test_should_remain_the_same(self):
        tri_map = require_file('test/samples/AL1.TRI')
        output = tri_map.to_raw_value()
        with open('test/samples/AL1.TRI', 'rb') as bdata:
            original = bdata.read()
            self.assertEqual(len(original), len(output))
            for i, x in enumerate(original):
                self.assertEqual(x, output[i], f"Wrong value at index {i}")
