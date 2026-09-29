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


class TestNfs4FrdMap(unittest.TestCase):

    def test_nfs4_frd_should_be_same_size_and_stable(self):
        (name, block, data) = require_file('test/samples/GT1.FRD')
        with open('test/samples/GT1.FRD', 'rb') as bdata:
            original = bdata.read()
        output = block.pack(data, name=name)
        # `polygon_vroad_data.normal`/`.forward` are re-normalized to unit length on write, which
        # is lossy (the source data isn't always exactly unit length in the first place), so a
        # byte-identical round trip isn't expected here - only that the size is preserved and the
        # result stabilizes (a handful of vectors sit close enough to a quantization boundary that
        # convergence takes one extra cycle, hence comparing the 2nd and 3rd cycle rather than the
        # 1st and 2nd).
        self.assertEqual(len(original), len(output))
        data_twice = block.unpack_from_bytes(output, name=name + '__twice')
        output_twice = block.pack(data_twice, name=name + '__twice')
        data_thrice = block.unpack_from_bytes(output_twice, name=name + '__thrice')
        output_thrice = block.pack(data_thrice, name=name + '__thrice')
        self.assertEqual(output_twice, output_thrice)
