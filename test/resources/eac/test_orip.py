import os
import tempfile
import unittest
from io import BytesIO

from library import require_file
from library.context import ReadContext
from library.exceptions import DataIntegrityException
from library.loader import clear_file_cache
from resources.eac.geometries.tnfs import NamedIndex

GOLDEN_CORPUS = os.path.join(os.path.dirname(__file__), '..', '..', 'golden_corpus')


class TestOripNames(unittest.TestCase):
    def test_garbage_name_is_written_back_as_read(self):
        # a DVIPER fx_polys entry: name bytes 80 02, not UTF-8
        raw = b'\x80\x02\x00\x00\x00\x00\x00\x00' + (84).to_bytes(4, 'little')
        block = NamedIndex()
        data = block.unpack(ReadContext(BytesIO(raw)))
        self.assertEqual(block.estimate_packed_size(data), 12)
        self.assertEqual(block.pack(data), raw)

    def test_renamed_entry_keeps_12_bytes(self):
        block = NamedIndex()
        data = block.unpack(ReadContext(BytesIO(b'lt_frnt\x00' + (3).to_bytes(4, 'little'))))
        data['name'] = 'lt'
        self.assertEqual(block.estimate_packed_size(data), 12)
        self.assertEqual(block.pack(data), b'lt\x00\x00\x00\x00\x00\x00' + (3).to_bytes(4, 'little'))
        data['name'] = 'too_long'
        with self.assertRaisesRegex(DataIntegrityException, 'longer than 7 bytes'):
            block.pack(data)

    def test_block_size_follows_renamed_labels(self):
        path = os.path.join(GOLDEN_CORPUS, 'JEEP.CFM')
        name, block, data = require_file(path, lazy=False)
        model = data['children'][0]['item']['data']
        model['labels'][0]['name'] = 'b'
        with tempfile.TemporaryDirectory() as tmp:
            saved = os.path.join(tmp, 'JEEP.CFM')
            with open(saved, 'wb') as f:
                f.write(block.pack(data, name=name))
            _, _, reread = require_file(saved, lazy=False)
            clear_file_cache(saved)
        model = reread['children'][0]['item']['data']
        self.assertEqual(model['resource_id'], 'ORIP')
        self.assertEqual(model['labels'][0]['name'], 'b')
        clear_file_cache(path)


class TestWwwwEmptyEntries(unittest.TestCase):
    def test_entry_without_data_is_written_with_offset_0(self):
        # TNFS FAM files mark an empty entry with offset 0 (NTRACKFM/CY3_M01.FAM)
        path = os.path.join(GOLDEN_CORPUS, 'JEEP.CFM')
        name, block, data = require_file(path, lazy=False)
        data['children'][3] = {'item': {'choice_index': block.bytes_choice, 'data': b''}, 'post_offset_payload': b''}
        packed = block.pack(data, name=name)
        self.assertEqual(int.from_bytes(packed[20:24], 'little'), 0)
        with tempfile.TemporaryDirectory() as tmp:
            saved = os.path.join(tmp, 'JEEP.CFM')
            with open(saved, 'wb') as f:
                f.write(packed)
            _, _, reread = require_file(saved, lazy=False)
            clear_file_cache(saved)
        self.assertEqual(reread['children'][3]['item']['data'], b'')
        self.assertEqual(reread['children'][2], data['children'][2])
        clear_file_cache(path)


if __name__ == '__main__':
    unittest.main()
