import unittest

from library import require_file


class TestCarPerformanceSpec(unittest.TestCase):

    def test_pbs_hash_can_be_reconstructed(self):
        (name, block, data) = require_file('test/samples/LDIABL.PBS__uncompressed')
        data['hash'] = None
        output = block.pack(data, name=name)
        with open('test/samples/LDIABL.PBS__uncompressed', 'rb') as bdata:
            original = bdata.read()
            self.assertEqual(len(original), len(output))
            for i, x in enumerate(original):
                self.assertEqual(x, output[i], f"Wrong value at index {i}")
