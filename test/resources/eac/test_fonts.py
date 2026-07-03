import unittest

from library import require_file
from resources.eac.bitmaps import EacImage


class TestFfnFont(unittest.TestCase):

    def test_old_ffn_should_remain_the_same(self):
        (name, block, font_res) = require_file('test/golden_corpus/GRAVER18.FFN')
        output = block.pack(font_res, name=name)
        with open('test/golden_corpus/GRAVER18.FFN', 'rb') as bdata:
            original = bdata.read()
            self.assertEqual(len(original), len(output))
            for i, x in enumerate(original):
                self.assertEqual(x, output[i], f"Wrong value at index {i}")

    def test_old_ffn_can_be_reconstructed_from_files(self):
        (name, block, font_res) = require_file('test/golden_corpus/GRAVER18.FFN')
        import tempfile
        from serializers import get_serializer
        serializer = get_serializer(block, font_res)
        self.assertTrue(serializer.ui_serialization()['reversible'])
        with tempfile.TemporaryDirectory() as tmp:
            output_files = serializer.serialize(font_res, tmp, name, block)
            font_res2 = serializer.deserialize(output_files, name, block=block)
            (EacImage()).action_convert_to_4bit(font_res2['bitmap'], '4Bit', 'alpha')
        output = block.pack(font_res2, name=name)
        with open('test/golden_corpus/GRAVER18.FFN', 'rb') as bdata:
            original = bdata.read()
            self.assertEqual(len(original), len(output))
            for i, x in enumerate(original):
                self.assertEqual(x, output[i], f"Wrong value at index {i}")

    def test_new_ffn_should_remain_the_same(self):
        (name, block, font_res) = require_file('test/golden_corpus/Arial12b.ffn')
        output = block.pack(font_res, name=name)
        with open('test/golden_corpus/Arial12b.ffn', 'rb') as bdata:
            original = bdata.read()
            self.assertEqual(len(original), len(output))
            for i, x in enumerate(original):
                self.assertEqual(x, output[i], f"Wrong value at index {i}")

    def test_new_ffn_can_be_reconstructed_from_files(self):
        (name, block, font_res) = require_file('test/golden_corpus/Arial12b.ffn')
        import tempfile
        from serializers import get_serializer
        serializer = get_serializer(block, font_res)
        self.assertTrue(serializer.ui_serialization()['reversible'])
        with tempfile.TemporaryDirectory() as tmp:
            output_files = serializer.serialize(font_res, tmp, name, block)
            font_res2 = serializer.deserialize(output_files, name, block=block)
            (EacImage()).action_convert_to_8bit(font_res2['bitmap'], 'alpha')
            # we don't set it as it is optional. In order to reconstruct this particular font exactly, we need to set it
            font_res2['bitmap']['block_size'] = 51264
        output = block.pack(font_res2, name=name)
        with open('test/golden_corpus/Arial12b.ffn', 'rb') as bdata:
            original = bdata.read()
            self.assertEqual(len(original), len(output))
            for i, x in enumerate(original):
                self.assertEqual(x, output[i], f"Wrong value at index {i}")
