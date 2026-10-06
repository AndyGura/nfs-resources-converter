import os
import unittest
from io import BytesIO

from library import require_file
from resources.blackbox.archives import NfsuJdlzCompressedBlock
from resources.blackbox.maps.nfsu import NfsuChunkBundle, NfsuTrackBundle
from resources.eac.compressions.jdlz import JdlzCompression
from serializers.bitmaps import nfsu_texture_pack_textures, nfsu_texture_to_image
from serializers.geometries import nfsu_geometry_meshes
from serializers.maps import NfsuWorld, find_nfsu_stream_file, nfsu_section_ranges, nfsu_streaming_sections

SECTION = 'test/samples/NFSU_B36.BUN'


def _chunk(data, key, value):
    return next(c['data'] for c in data['chunks'] if c['data'].get(key) == value)


class TestNfsuChunkBundle(unittest.TestCase):
    def test_section_should_be_read_and_remain_the_same(self):
        (name, block, data) = require_file(SECTION)
        self.assertIsInstance(block, NfsuChunkBundle)
        with open(SECTION, 'rb') as f:
            self.assertEqual(f.read(), block.pack(data, name=name))

    def test_scenery_instances_should_reference_meshes_of_the_section(self):
        (_, _, data) = require_file(SECTION)
        world = NfsuWorld()
        world.collect(data)
        self.assertEqual(len(world.sceneries), 1)
        section_number, infos, instances = world.sceneries[0]
        self.assertEqual(section_number, 236)
        self.assertTrue(instances)
        for instance in instances:
            # rotation with scale
            self.assertTrue(all(-4 < x < 4 for x in instance['rotation']))
            self.assertLess(instance['info_index'], len(infos))
        # other objects use meshes of other sections (shared ones)
        self.assertTrue(any(infos[x['info_index']]['mesh_ids'][0] in world.meshes for x in instances))
        parts = world.scenery_parts(infos, instances)
        self.assertTrue(parts)
        self.assertTrue(any(texture_id in world.textures for texture_id in parts))
        for texture_id, (vertices, uvs, triangles) in parts.items():
            self.assertEqual(len(vertices), len(uvs))
            self.assertLess(triangles.max(), len(vertices))

    def test_mesh_materials_should_cover_all_triangles(self):
        (_, _, data) = require_file(SECTION)
        geometry = _chunk(data, 'header', 0x80134000)
        meshes = nfsu_geometry_meshes(geometry)
        self.assertTrue(meshes)
        for mesh in meshes:
            for _, triangles in mesh.parts:
                self.assertTrue(all(0 <= i < len(mesh.vertices) for t in triangles for i in t))

    def test_texture_should_be_decoded(self):
        (_, _, data) = require_file(SECTION)
        textures = nfsu_texture_pack_textures(_chunk(data, 'chunk_id', 0xB3300000))
        self.assertEqual([t[0]['name'] for t in textures], ['ARC_BUILD_135'])
        info, d3d_format, image_data = textures[0]
        self.assertEqual(d3d_format, int.from_bytes(b'DXT1', 'little'))
        image = nfsu_texture_to_image(info, d3d_format, image_data)
        self.assertEqual(image.size, (128, 128))
        # a building facade: not a flat color
        self.assertGreater(len(set(image.getdata())), 100)


class TestJdlz(unittest.TestCase):
    def test_compressed_data_should_be_uncompressed_back(self):
        compression = JdlzCompression()
        for raw in [b'', b'a', b'abc' * 1000, bytes(range(256)) * 20, open(SECTION, 'rb').read()]:
            compressed = compression.compress(BytesIO(raw), len(raw))
            self.assertEqual(compressed[:4], b'JDLZ')
            self.assertEqual(int.from_bytes(compressed[12:16], 'little'), len(compressed))
            self.assertEqual(compression.uncompress(BytesIO(compressed), len(compressed)), raw)

    def test_compressed_bundle_should_be_read(self):
        with open(SECTION, 'rb') as f:
            raw = f.read()
        compressed = JdlzCompression().compress(BytesIO(raw), len(raw))
        block = NfsuJdlzCompressedBlock()
        data = block.unpack_from_bytes(compressed, name='test.lzc')
        self.assertIsInstance(block.possible_blocks[data['choice_index']], NfsuChunkBundle)
        packed = block.pack(data)
        self.assertEqual(JdlzCompression().uncompress(BytesIO(packed), len(packed)), raw)


NFSU2_DIR = 'test/samples/claude_tmp/nfsu2'


@unittest.skipUnless(os.path.exists(f'{NFSU2_DIR}/L4RA.BUN'), f'needs NFSU2 samples in {NFSU2_DIR}')
class TestNfsu2LocationBundle(unittest.TestCase):
    def test_location_bundle_should_be_read_and_remain_the_same(self):
        path = f'{NFSU2_DIR}/L4RA.BUN'
        (name, block, data) = require_file(path)
        self.assertIsInstance(block, NfsuTrackBundle)
        with open(path, 'rb') as f:
            self.assertEqual(f.read(), block.pack(data, name=name))

    def test_streaming_sections_should_be_listed(self):
        (_, _, data) = require_file(f'{NFSU2_DIR}/L4RA.BUN')
        sections = nfsu_streaming_sections(data)
        ranges = nfsu_section_ranges(sections)
        self.assertEqual(len(ranges), 392)
        self.assertNotIn('--', [s['name'] for s in ranges])
        stream_end = max(s['offset'] + s['size'] for s in ranges)
        stream_path = f'{NFSU2_DIR}/STREAML4RA.BUN'
        if os.path.exists(stream_path):
            self.assertEqual(find_nfsu_stream_file(f'{NFSU2_DIR}/L4RA.BUN', sections), stream_path)
            self.assertGreaterEqual(os.path.getsize(stream_path), stream_end)

    @unittest.skipUnless(os.path.exists(f'{NFSU2_DIR}/STREAML4RA.BUN'), 'needs NFSU2 STREAML4RA.BUN')
    def test_streamed_section_should_be_read_and_remain_the_same(self):
        (_, _, data) = require_file(f'{NFSU2_DIR}/L4RA.BUN')
        section = next(s for s in nfsu_section_ranges(nfsu_streaming_sections(data)) if s['name'] == 'C22')
        with open(f'{NFSU2_DIR}/STREAML4RA.BUN', 'rb') as f:
            f.seek(section['offset'])
            raw = f.read(section['size'])
        block = NfsuChunkBundle()
        section_data = block.unpack_from_bytes(raw, name='section.BUN')
        self.assertEqual(raw, block.pack(section_data))
        world = NfsuWorld()
        world.collect(section_data)
        # NFSU2 scenery layout: named infos, instances with float bounding box
        self.assertEqual(len(world.sceneries), 2)
        for _, infos, instances in world.sceneries:
            self.assertTrue(all(i['name'] for i in infos))
            self.assertTrue(all(0 <= x['info_index'] < len(infos) for x in instances))
