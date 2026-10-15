import unittest
from copy import deepcopy

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
                self.assertEqual(x, output[i], f'Wrong value at index {i}')

    def test_old_ffn_can_be_reconstructed_from_files(self):
        (name, block, font_res) = require_file('test/golden_corpus/GRAVER18.FFN')
        import tempfile
        from serializers import get_serializer

        serializer = get_serializer(block, font_res)
        self.assertTrue(serializer.ui_serialization()['reversible'])
        with tempfile.TemporaryDirectory() as tmp:
            output_files = serializer.serialize(font_res, tmp, name, block)
            font_res2 = serializer.deserialize(output_files, name, block=block)
        self.assertEqual(font_res2['bitmap']['resource_id'], '4Bit')
        output = block.pack(font_res2, name=name)
        with open('test/golden_corpus/GRAVER18.FFN', 'rb') as bdata:
            original = bdata.read()
            self.assertEqual(len(original), len(output))
            for i, x in enumerate(original):
                self.assertEqual(x, output[i], f'Wrong value at index {i}')

    def test_new_ffn_should_remain_the_same(self):
        (name, block, font_res) = require_file('test/golden_corpus/Arial12b.ffn')
        output = block.pack(font_res, name=name)
        with open('test/golden_corpus/Arial12b.ffn', 'rb') as bdata:
            original = bdata.read()
            self.assertEqual(len(original), len(output))
            for i, x in enumerate(original):
                self.assertEqual(x, output[i], f'Wrong value at index {i}')

    def test_new_ffn_can_be_reconstructed_from_files(self):
        (name, block, font_res) = require_file('test/golden_corpus/Arial12b.ffn')
        import tempfile
        from serializers import get_serializer

        serializer = get_serializer(block, font_res)
        self.assertTrue(serializer.ui_serialization()['reversible'])
        with tempfile.TemporaryDirectory() as tmp:
            output_files = serializer.serialize(font_res, tmp, name, block)
            font_res2 = serializer.deserialize(output_files, name, block=block)
        self.assertEqual(font_res2['bitmap']['resource_id'], '8Bit')
        output = block.pack(font_res2, name=name)
        with open('test/golden_corpus/Arial12b.ffn', 'rb') as bdata:
            original = bdata.read()
            self.assertEqual(len(original), len(output))
            for i, x in enumerate(original):
                self.assertEqual(x, output[i], f'Wrong value at index {i}')

    def test_16_bytes_ffn_kern_index_points_to_pairs_of_right_glyph(self):
        (name, block, font_res) = require_file('test/golden_corpus/Arial12b.ffn')
        font = deepcopy(font_res)
        font['flags']['format'] = '16-bytes'
        for glyph in font['definitions']:
            glyph['kern_index'] = 0
            glyph['x_advance'] = glyph['advance']
        # removed first pair, added a pair at the end, reversed order: the writer sorts pairs by right glyph again
        font['kernings'] = list(reversed(font['kernings'][1:])) + [{'left': ord('T'), 'kerning': -1, 'right': ord('A')}]
        written = block.unpack_from_bytes(block.pack(font, name=name))
        kernings = written['kernings']
        rights = [x['right'] for x in kernings]
        self.assertEqual(rights, sorted(rights))
        for glyph in written['definitions']:
            pairs = [i for i, x in enumerate(kernings) if x['right'] == glyph['code']]
            self.assertEqual(glyph['num_kern'], len(pairs))
            self.assertEqual(glyph['kern_index'], pairs[0] if pairs else 0)
            self.assertEqual(pairs, list(range(glyph['kern_index'], glyph['kern_index'] + len(pairs))))

    def test_glyphs_are_written_sorted_by_code(self):
        (name, block, font_res) = require_file('test/golden_corpus/Arial12b.ffn')
        font = deepcopy(font_res)
        font['definitions'] = list(reversed(font['definitions']))
        written = block.unpack_from_bytes(block.pack(font, name=name))
        self.assertEqual(written['definitions'], font_res['definitions'])

    def test_import_refuses_kerning_right_glyph_above_255(self):
        (name, block, font_res) = require_file('test/golden_corpus/Arial12b.ffn')
        import tempfile
        from library.exceptions import SerializationException
        from serializers import get_serializer

        serializer = get_serializer(block, font_res)
        with tempfile.TemporaryDirectory() as tmp:
            output_files = serializer.serialize(font_res, tmp, name, block)
            fnt_path = next(x for x in output_files if x.endswith('.fnt'))
            with open(fnt_path, 'a') as f:
                f.write('kerning first=65 second=1046 amount=-1\n')
            with self.assertRaises(SerializationException) as cm:
                serializer.deserialize(output_files, name, block=block)
        self.assertIn('second=1046', str(cm.exception))

    def test_added_glyph_keeps_bitmap_alignment(self):
        for path, align, residue, fill in [
            ('test/golden_corpus/GRAVER18.FFN', 16, 0, b'\xad'),
            ('test/golden_corpus/Arial12b.ffn', 128, 112, b'Buy ERTS'),
        ]:
            (name, block, font_res) = require_file(path)
            font = deepcopy(font_res)
            glyph = deepcopy(font['definitions'][-1])
            glyph['code'] += 1
            font['definitions'].append(glyph)
            written = block.unpack_from_bytes(block.pack(font, name=name))
            self.assertEqual(written['bdata_ptr'] % align, residue, path)
            self.assertTrue(bytes(written['padding_2']).startswith(fill[: len(written['padding_2'])]), path)
            self.assertEqual(written['bitmap'], font_res['bitmap'], path)

    def _export_fnt(self, font_res, block, name, tmp, keep_custom=True):
        from serializers import get_serializer

        serializer = get_serializer(block, font_res)
        output_files = serializer.serialize(font_res, tmp, name, block)
        fnt_path = next(x for x in output_files if x.endswith('.fnt'))
        if not keep_custom:
            with open(fnt_path) as f:
                lines = [l for l in f if not l.startswith('#custom')]
            with open(fnt_path, 'w') as f:
                f.writelines(lines)
        return serializer, fnt_path

    def test_bmfont_import_keeps_header_of_replaced_font(self):
        import tempfile

        (name, block, font_res) = require_file('test/golden_corpus/Arial12b.ffn')
        with tempfile.TemporaryDirectory() as tmp:
            serializer, fnt_path = self._export_fnt(font_res, block, name, tmp, keep_custom=False)
            # only the .fnt: the PNG is found from its page line
            imported = serializer.deserialize([fnt_path], name, block=block)
            self.assertEqual(block.pack(imported, name=name), block.pack(font_res, name=name))
            # no font loaded under the id: a new font gets version 100
            imported = serializer.deserialize([fnt_path], 'not/loaded.ffn', block=block)
            self.assertEqual(imported['version'], 100)

    def test_import_explains_missing_atlas(self):
        import os
        import tempfile
        from library.exceptions import SerializationException

        (name, block, font_res) = require_file('test/golden_corpus/GRAVER18.FFN')
        with tempfile.TemporaryDirectory() as tmp:
            serializer, fnt_path = self._export_fnt(font_res, block, name, tmp)
            os.remove(os.path.join(tmp, 'bitmap.png'))
            with self.assertRaises(SerializationException) as cm:
                serializer.deserialize([fnt_path], name, block=block)
        self.assertIn('Pick the PNG together with the .fnt', str(cm.exception))

    def test_new_font_has_version_100(self):
        from resources.eac.fonts import FfnFont

        self.assertEqual(FfnFont().new_data()['version'], 100)
