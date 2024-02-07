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
        fsh['children_count'] = 0
        fsh['children_descriptions'] = []
        output = block.pack(fsh, name=name)
        with open('test/samples/VERTBST.FSH', 'rb') as bdata:
            original = bdata.read()
            self.assertEqual(len(original), len(output))
            for i, x in enumerate(original):
                self.assertEqual(x, output[i], f"Wrong value at index {i}")


class TestWwwwBlock(unittest.TestCase):

    def test_cfm_should_remain_the_same(self):
        (name, block, res) = require_file('test/samples/LDIABL.CFM')
        output = block.pack(res, name=name)
        with open('test/samples/LDIABL.CFM', 'rb') as bdata:
            original = bdata.read()
            self.assertEqual(len(original), len(output))
            for i, x in enumerate(original):
                self.assertEqual(x, output[i], f"Wrong value at index {i}")

    def test_cfm_should_reconstruct_offsets(self):
        (name, block, res) = require_file('test/samples/LDIABL.CFM')
        res['children_offsets'] = []
        res['children_count'] = 0
        res['children'][1]['data']['children_descriptions'] = []
        output = block.pack(res, name=name)
        with open('test/samples/LDIABL.CFM', 'rb') as bdata:
            original = bdata.read()
            self.assertEqual(len(original), len(output))
            for i, x in enumerate(original):
                self.assertEqual(x, output[i], f"Wrong value at index {i}")
