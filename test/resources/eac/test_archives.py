import unittest

from library import require_file


class TestShpiBlock(unittest.TestCase):

    def test_fsh_should_remain_the_same(self):
        (name, block, fsh) = require_file('test/samples/VERTBST.FSH')
        output = block.pack(fsh, name=name)
        with open('test/samples/VERTBST.FSH', 'rb') as bdata:
            original = bdata.read()
            self.assertEqual(len(original), len(output))
            for i, x in enumerate(original):
                self.assertEqual(x, output[i], f"Wrong value at index {i}")

    def test_fsh_should_reconstruct_offsets(self):
        (name, block, fsh) = require_file('test/samples/VERTBST.FSH')
        fsh['num_items'] = 0
        fsh['items_descr'] = []
        output = block.pack(fsh, name=name)
        with open('test/samples/VERTBST.FSH', 'rb') as bdata:
            original = bdata.read()
            self.assertEqual(len(original), len(output))
            for i, x in enumerate(original):
                self.assertEqual(x, output[i], f"Wrong value at index {i}")


class TestWwwwBlock(unittest.TestCase):

    def test_cfm_should_remain_the_same(self):
        (name, block, res) = require_file('test/samples/TSUPRA.CFM')
        output = block.pack(res, name=name)
        with open('test/samples/TSUPRA.CFM', 'rb') as bdata:
            original = bdata.read()
            self.assertEqual(len(original), len(output))
            for i, x in enumerate(original):
                self.assertEqual(x, output[i], f"Wrong value at index {i}")

    def test_cfm_should_reconstruct_offsets(self):
        (name, block, res) = require_file('test/samples/TSUPRA.CFM')
        res['items_descr'] = []
        res['num_items'] = 0
        res['children'][1]['data']['items_descr'] = []
        output = block.pack(res, name=name)
        with open('test/samples/TSUPRA.CFM', 'rb') as bdata:
            original = bdata.read()
            self.assertEqual(len(original), len(output))
            for i, x in enumerate(original):
                self.assertEqual(x, output[i], f"Wrong value at index {i}")


class TestSoundBankBlock(unittest.TestCase):

    def test_bnk_should_remain_the_same(self):
        (name, block, res) = require_file('test/samples/DIABLOSW.BNK')
        output = block.pack(res, name=name)
        with open('test/samples/DIABLOSW.BNK', 'rb') as bdata:
            original = bdata.read()
            self.assertEqual(len(original), len(output))
            for i, x in enumerate(original):
                self.assertEqual(x, output[i], f"Wrong value at index {i}")


class TestBigfBlock(unittest.TestCase):

    def test_bigf_should_remain_the_same(self):
        (name, block, res) = require_file('test/samples/CARDATA.VIV')
        output = block.pack(res, name=name)
        with open('test/samples/CARDATA.VIV', 'rb') as bdata:
            original = bdata.read()
            self.assertEqual(len(original), len(output))
            for i, x in enumerate(original):
                self.assertEqual(x, output[i], f"Wrong value at index {i}")
