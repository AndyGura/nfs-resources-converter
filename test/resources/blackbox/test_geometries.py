import os
import unittest

from library import require_file
from serializers.bitmaps import nfsu_texture_pack_textures, nfsu_texture_to_image
from serializers.geometries import bin_hash, find_nfsu_car_textures, nfsmw_car_runtime_texture, nfsu_geometry_meshes

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
        (name, block, data) = require_file('test/samples/NFSU_B36.BUN', lazy=False)
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


NFSU2_CAR_DIR = 'test/samples/claude_tmp/nfsu2/CARS/SUPRA'


@unittest.skipUnless(os.path.exists(f'{NFSU2_CAR_DIR}/GEOMETRY.BIN'), f'needs NFSU2 car samples in {NFSU2_CAR_DIR}')
class TestNfsu2CarGeometry(unittest.TestCase):
    def test_geometry_should_remain_the_same(self):
        path = f'{NFSU2_CAR_DIR}/GEOMETRY.BIN'
        (name, block, data) = require_file(path, lazy=False)
        with open(path, 'rb') as f:
            self.assertEqual(f.read(), block.pack(data, name=name))
        meshes = nfsu_geometry_meshes(data)
        self.assertIn('SUPRA_KIT00_BODY_A', [m.name for m in meshes])
        for mesh in meshes:
            for _, triangles in mesh.parts:
                self.assertTrue(all(0 <= i < len(mesh.vertices) for t in triangles for i in t))

    def test_compressed_textures_should_be_decoded(self):
        # car TEXTURES.BIN holds JDLZ- and HUFF-compressed textures; CARS/TEXTURES.BIN and GLOBALB.LZC are shared
        textures = find_nfsu_car_textures(f'{NFSU2_CAR_DIR}/GEOMETRY.BIN')
        names = {info['name'] for info, _, _ in textures.values()}
        self.assertIn('SUPRA_BADGING', names)
        self.assertIn('SUPRA_TIRE', names)
        self.assertIn('CHROME', names)
        (_, _, data) = require_file(f'{NFSU2_CAR_DIR}/TEXTURES.BIN')
        tpk = next(c['data'] for c in data['chunks'] if c['data'].get('chunk_id') == 0xB3300000)
        car_textures = nfsu_texture_pack_textures(tpk)
        self.assertEqual(len(car_textures), 71)
        for info, d3d_format, image_data in car_textures:
            image = nfsu_texture_to_image(info, d3d_format, image_data)
            self.assertEqual(image.size, (info['width'], info['height']))


class TestNfsmwWorldGeometry(unittest.TestCase):
    def test_world_section_should_be_read_and_remain_the_same(self):
        # a streamed section of NFSMW world (STREAML2RA.BUN): meshes with several vertex buffers (one per effect),
        # 36- and 60-byte vertices, null-terminated mesh names
        path = 'test/samples/NFSMW_C52.BUN'
        (name, block, data) = require_file(path, lazy=False)
        with open(path, 'rb') as f:
            self.assertEqual(f.read(), block.pack(data, name=name))
        geometry = next(c['data'] for c in data['chunks'] if c['data'].get('header') == 0x80_13_40_00)
        self.assertEqual(sorted(c['vertices']['choice_index'] for c in _vertices_chunks(geometry)), [0, 2, 2, 2, 2, 2])
        meshes = nfsu_geometry_meshes(geometry)
        self.assertTrue(meshes)
        for mesh in meshes:
            self.assertTrue(mesh.name)
            for _, triangles in mesh.parts:
                self.assertTrue(all(0 <= i < len(mesh.vertices) for t in triangles for i in t))


NFSMW_CAR_DIR = 'test/samples/claude_tmp/nfsmw/Cars/BMWM3GTR'


@unittest.skipUnless(os.path.exists(f'{NFSMW_CAR_DIR}/GEOMETRY.BIN'), f'needs NFSMW car samples in {NFSMW_CAR_DIR}')
class TestNfsmwCarGeometry(unittest.TestCase):
    def test_geometry_should_remain_the_same(self):
        path = f'{NFSMW_CAR_DIR}/GEOMETRY.BIN'
        (name, block, data) = require_file(path, lazy=False)
        with open(path, 'rb') as f:
            self.assertEqual(f.read(), block.pack(data, name=name))
        meshes = nfsu_geometry_meshes(data)
        self.assertEqual(len(meshes), 97)
        self.assertIn('BMWM3GTR_KIT00_BODY_A', [m.name for m in meshes])

    def test_every_texture_should_be_found(self):
        # light, window and driver textures are run time slots, shown as the car's textures in the default state
        path = f'{NFSMW_CAR_DIR}/GEOMETRY.BIN'
        (_, _, data) = require_file(path)
        textures = find_nfsu_car_textures(path)
        missing = set()
        for mesh in nfsu_geometry_meshes(data):
            for texture_id, _ in mesh.parts:
                if nfsmw_car_runtime_texture(texture_id, mesh.name, textures) not in textures:
                    missing.add(texture_id)
        # body paint (BMWM3GTR_SKIN1) is made by the game
        self.assertEqual(missing, {bin_hash('BMWM3GTR_SKIN1')})
        light = nfsmw_car_runtime_texture(bin_hash('BRAKELIGHT_LEFT'), 'BMWM3GTR_KIT00_LEFT_BRAKELIGHT_A', textures)
        self.assertEqual(light, bin_hash('BMWM3GTR_KIT00_BRAKELIGHT_OFF'))
