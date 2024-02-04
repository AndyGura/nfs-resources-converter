import unittest

from library import require_file


class TestSerializeDeserialize(unittest.TestCase):

    def test_tri_should_remain_the_same(self):
        (name, block, tri) = require_file('test/samples/AL1.TRI')
        output = block.pack(tri, name=name)
        with open('test/samples/AL1.TRI', 'rb') as bdata:
            original = bdata.read()
            self.assertEqual(len(original), len(output))
            for i, x in enumerate(original):
                self.assertEqual(x, output[i], f"Wrong value at index {i}")

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

    def test_ffn_should_remain_the_same(self):
        (name, block, font_res) = require_file('test/samples/MAIN24.FFN')
        output = block.pack(font_res, name=name)
        with open('test/samples/MAIN24.FFN', 'rb') as bdata:
            original = bdata.read()
            self.assertEqual(len(original), len(output))
            for i, x in enumerate(original):
                self.assertEqual(x, output[i], f"Wrong value at index {i}")

    def test_ffn_can_be_reconstructed_from_files(self):
        (name, block, font_res) = require_file('test/samples/MAIN24.FFN')
        import tempfile
        from serializers import get_serializer
        serializer = get_serializer(block, font_res)
        self.assertTrue(serializer.setup_for_reversible_serialization())
        with tempfile.TemporaryDirectory() as tmp:
            serializer.serialize(font_res, tmp, name, block)
            font_res = serializer.deserialize(tmp, name, block=block)
        output = block.pack(font_res, name=name)
        with open('test/samples/MAIN24.FFN', 'rb') as bdata:
            original = bdata.read()
            self.assertEqual(len(original), len(output))
            for i, x in enumerate(original):
                self.assertEqual(x, output[i], f"Wrong value at index {i}")
