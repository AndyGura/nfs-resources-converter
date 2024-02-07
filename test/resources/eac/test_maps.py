import unittest

from library import require_file


class TestTriMap(unittest.TestCase):

    def test_tri_should_remain_the_same(self):
        (name, block, tri) = require_file('test/samples/AL1.TRI')
        output = block.pack(tri, name=name)
        with open('test/samples/AL1.TRI', 'rb') as bdata:
            original = bdata.read()
            self.assertEqual(len(original), len(output))
            for i, x in enumerate(original):
                self.assertEqual(x, output[i], f"Wrong value at index {i}")
