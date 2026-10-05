import unittest
from io import BytesIO
from os.path import getsize

from library.read_blocks import DataBlock
from resources.eac.compressions.ref_pack import RefPackCompression
from resources.eac.geometries.nfs5 import CrpGeometry


class TestCrpGeometry(unittest.TestCase):
    @unittest.skip
    def test_crp_should_remain_the_same(self):
        compression = RefPackCompression()
        b = open('test/samples/356b.crp', 'rb', buffering=100 * 1024 * 1024)
        uncompressed = compression.uncompress(b, getsize('test/samples/356b.crp'))

        block = CrpGeometry()
        DataBlock.root_read_ctx.buffer = BytesIO(uncompressed)
        DataBlock.root_read_ctx.read_start_offset = 0
        DataBlock.root_read_ctx.read_bytes_amount = len(uncompressed)
        data = block.unpack(DataBlock.root_read_ctx, name='356b.crp', read_bytes_amount=len(uncompressed))
        output = block.pack(data, name='356b.crp')

        self.assertEqual(len(uncompressed), len(output))
        for i, x in enumerate(uncompressed):
            self.assertEqual(x, output[i], f'Wrong value at index {i}')


def build_fce3_data():
    """Minimal FCE3 model: part 0 is a quad (2 triangles), part 1 is a semi-transparent double-sided triangle,
    one dummy"""
    from resources.eac.geometries.nfs3 import Fce3Geometry

    block = Fce3Geometry()
    data = block.new_data()
    data['num_parts'] = 2
    data['part_names'][0] = ':HB'
    data['part_names'][1] = ':HLFW'
    data['part_positions'][1] = {'x': 1.0, 'y': 2.0, 'z': 3.0}
    data['part_first_vertex'][:2] = [0, 4]
    data['part_num_vertices'][:2] = [4, 3]
    data['part_first_triangle'][:2] = [0, 2]
    data['part_num_triangles'][:2] = [2, 1]
    data['num_dummies'] = 1
    data['dummy_names'][0] = 'HFLO'
    data['dummy_positions'][0] = {'x': 0.5, 'y': 0.25, 'z': 2.0}
    data['num_arts'] = 1
    vertices = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0), (0, 0, 0), (1, 0, 0), (0, 0, 1)]
    data['vertices'] = [{'x': x, 'y': y, 'z': z} for x, y, z in vertices]
    data['normals'] = [{'x': 0.0, 'y': 1.0, 'z': 0.0} for _ in vertices]
    data['triangles'] = []
    for vertex_indices, semi_transparent in [([0, 1, 2], False), ([0, 2, 3], False), ([0, 1, 2], True)]:
        triangle = block.field_blocks_map['triangles'].child.new_data()
        triangle['vertex_indices'] = vertex_indices
        triangle['unk0'] = [0xFF00, 0xFF00, 0xFF00]
        triangle['flags']['semi_transparent'] = semi_transparent
        triangle['flags']['no_cull'] = semi_transparent
        triangle['u'] = [0.0, 0.5, 1.0]
        triangle['v'] = [0.25, 0.5, 0.75]
        data['triangles'].append(triangle)
    data['reserve1'] = bytes(32 * len(vertices))
    data['reserve2'] = bytes(12 * len(vertices))
    data['reserve3'] = bytes(12 * len(vertices))
    return block, data


class TestFce3Geometry(unittest.TestCase):
    def test_round_trip(self):
        block, data = build_fce3_data()
        packed = block.pack(data)
        self.assertEqual(len(packed), 0x1F04 + 7 * (12 + 12 + 32 + 12 + 12) + 3 * 56)
        read = block.unpack_from_bytes(packed)
        self.assertEqual(read['num_vertices'], 7)
        self.assertEqual(read['num_triangles'], 3)
        self.assertEqual(read['triangles_offset'], 7 * 24)
        self.assertEqual(read['reserve3_offset'], 7 * 68 + 3 * 56)
        self.assertEqual(read['part_names'][1], ':HLFW')
        self.assertEqual(read['dummy_names'][0], 'HFLO')
        self.assertEqual(read['triangles'][2]['vertex_indices'], [0, 1, 2])
        self.assertTrue(read['triangles'][2]['flags']['semi_transparent'])
        self.assertEqual(block.pack(read), packed)

    def test_detected_by_extension(self):
        from library.loader import probe_block_class
        from resources.eac.geometries import Fce3Geometry

        block, data = build_fce3_data()
        packed = block.pack(data)
        self.assertEqual(probe_block_class(BytesIO(packed), 'CAR.FCE', len(packed)), Fce3Geometry)

    def test_fce4_is_not_detected_as_fce3(self):
        from library.loader import probe_block_class
        from resources.eac.geometries import Fce4Geometry

        block, data = build_fce4_data()
        packed = block.pack(data)
        self.assertEqual(probe_block_class(BytesIO(packed), 'car.fce', len(packed)), Fce4Geometry)


def build_fce4_data():
    """Minimal FCE4 model: body (":HB") is a quad (2 triangles) with damaged position, front left wheel (":HLFW") is
    a triangle, one light dummy"""
    from resources.eac.geometries.nfs4 import Fce4Geometry

    block = Fce4Geometry()
    data = block.new_data()
    data['version'] = 0x00101014
    data['num_parts'] = 2
    data['part_names'][0] = ':HB'
    data['part_names'][1] = ':HLFW'
    data['part_positions'][1] = {'x': 1.0, 'y': 2.0, 'z': 3.0}
    data['part_first_vertex'][:2] = [0, 4]
    data['part_num_vertices'][:2] = [4, 3]
    data['part_first_triangle'][:2] = [0, 2]
    data['part_num_triangles'][:2] = [2, 1]
    data['num_dummies'] = 1
    data['dummy_names'][0] = 'HWYN5'
    data['num_colors'] = 1
    data['primary_colors'][0] = {'hue': 0, 'saturation': 255, 'brightness': 255, 'transparency': 0}
    data['num_arts'] = 1
    vertices = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0), (0, 0, 0), (1, 0, 0), (0, 0, 1)]
    data['vertices'] = [{'x': x, 'y': y, 'z': z} for x, y, z in vertices]
    data['normals'] = [{'x': 0.0, 'y': 1.0, 'z': 0.0} for _ in vertices]
    data['undamaged_vertices'] = [dict(v) for v in data['vertices']]
    data['undamaged_normals'] = [dict(v) for v in data['normals']]
    data['damaged_vertices'] = [dict(v) for v in data['vertices']]
    data['damaged_vertices'][2] = {'x': 0.75, 'y': 0.75, 'z': -0.5}
    data['damaged_normals'] = [dict(v) for v in data['normals']]
    data['triangles'] = []
    for vertex_indices in [[0, 1, 2], [0, 2, 3], [0, 1, 2]]:
        triangle = block.field_blocks_map['triangles'].child.new_data()
        triangle['vertex_indices'] = vertex_indices
        triangle['unk0'] = [0xFF00FF00, 0xFF00FF00, 0xFF00FF00]
        triangle['u'] = [0.0, 0.5, 1.0]
        triangle['v'] = [0.25, 0.5, 0.75]
        data['triangles'].append(triangle)
    data['triangles'][0]['flags']['window'] = True
    data['triangles'][0]['flags']['broken_window'] = True
    data['reserve1'] = bytes(32 * len(vertices))
    data['reserve2'] = bytes(12 * len(vertices))
    data['reserve3'] = bytes(12 * len(vertices))
    data['reserve4'] = bytes(4 * len(vertices))
    data['animation_flags'] = [0, 0, 0, 0, 4, 4, 4]
    data['reserve5'] = bytes(4 * len(vertices))
    data['reserve6'] = bytes(12 * 3)
    return block, data


class TestFce4Geometry(unittest.TestCase):
    def test_round_trip(self):
        block, data = build_fce4_data()
        packed = block.pack(data)
        self.assertEqual(len(packed), 0x2038 + 7 * (12 * 8 + 32 + 4 * 3) + 3 * (56 + 12))
        self.assertEqual(packed[:4], b'\x14\x10\x10\x00')
        read = block.unpack_from_bytes(packed)
        self.assertEqual(read['num_vertices'], 7)
        self.assertEqual(read['num_triangles'], 3)
        self.assertEqual(read['triangles_offset'], 7 * 24)
        self.assertEqual(read['damaged_vertices_offset'], 7 * (24 + 32 + 24 + 24) + 3 * 56)
        self.assertEqual(read['reserve6_offset'], 7 * (12 * 8 + 32 + 4 * 3) + 3 * 56)
        self.assertEqual(read['part_names'][1], ':HLFW')
        self.assertEqual(read['dummy_names'][0], 'HWYN5')
        self.assertEqual(read['primary_colors'][0], {'hue': 0, 'saturation': 255, 'brightness': 255, 'transparency': 0})
        self.assertEqual(read['damaged_vertices'][2], {'x': 0.75, 'y': 0.75, 'z': -0.5})
        self.assertEqual(read['animation_flags'], [0, 0, 0, 0, 4, 4, 4])
        self.assertTrue(read['triangles'][0]['flags']['broken_window'])
        self.assertEqual(block.pack(read), packed)

    def test_fce4m_has_longer_reserve6(self):
        block, data = build_fce4_data()
        data['version'] = 0x00101015
        data['reserve6'] = bytes(12 * 3 + 7)
        packed = block.pack(data)
        read = block.unpack_from_bytes(packed)
        self.assertEqual(len(read['reserve6']), 12 * 3 + 7)
        self.assertEqual(block.pack(read), packed)
