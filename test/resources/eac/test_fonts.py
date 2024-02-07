import unittest

from library import require_file


class TestFfnFont(unittest.TestCase):

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
