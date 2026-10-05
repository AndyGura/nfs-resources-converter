import unittest

from library import require_file

VERTICES_CHUNK_ID = 0x00_13_4B_01


def _vertices_chunks(data):
    for c in data['chunks']:
        if c['data']['chunk_id'] != 0x80_13_40_10:
            continue
        for sc in c['data']['sub_chunks']:
            if sc['data']['chunk_id'] != 0x80_13_41_00:
                continue
            for x in sc['data']['sub_chunks']:
                if x['data']['chunk_id'] == VERTICES_CHUNK_ID:
                    yield x['data']


class TestNfsuGeometry(unittest.TestCase):
    def test_geometry_should_remain_the_same(self):
        (name, block, data) = require_file('test/samples/GEOMETRY.BIN')
        output = block.pack(data, name=name)
        with open('test/samples/GEOMETRY.BIN', 'rb') as bdata:
            original = bdata.read()
        self.assertEqual(original, output)
        self.assertTrue(all(c['vertices']['choice_index'] == 0 for c in _vertices_chunks(data)))

    def test_world_meshes_with_24_byte_vertices_should_be_read_and_remain_the_same(self):
        # a streamed section of NFSU world (STREAML1RA.BUN): its geometry pack has 24-byte vertices without normal
        (name, block, data) = require_file('test/samples/NFSU_B36.BUN')
        with open('test/samples/NFSU_B36.BUN', 'rb') as bdata:
            original = bdata.read()
        self.assertEqual(original, block.pack(data, name=name))
        geometry = next(c['data'] for c in data['chunks'] if c['data'].get('header') == 0x80_13_40_00)
        chunks = list(_vertices_chunks(geometry))
        self.assertTrue(chunks)
        self.assertTrue(all(c['vertices']['choice_index'] == 1 for c in chunks))
        for c in chunks:
            # alignment filler makes vertices start at an offset aligned to 128 bytes
            self.assertEqual(c['elevens'], b'\x11' * len(c['elevens']))
            self.assertLess(len(c['elevens']), 128)
