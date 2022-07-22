import unittest

from library import require_file


class TestTRISerializeDeserialize(unittest.TestCase):

    def test_should_remain_the_same(self):
        tri_map = require_file('samples/AL1.TRI')
        output = tri_map.to_raw_value()
        with open('samples/AL1.TRI', 'rb') as bdata:
            original = bdata.read()
            for i, x in enumerate(original):
                self.assertEqual(x, output[i], f"Wrong value at index {i}")
