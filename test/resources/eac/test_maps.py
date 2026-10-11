import unittest
from copy import deepcopy

from library import require_file


class TestTriMap(unittest.TestCase):
    def test_tri_should_remain_the_same(self):
        (name, block, tri) = require_file('test/samples/AL1.TRI')
        output = block.pack(tri, name=name)
        with open('test/samples/AL1.TRI', 'rb') as bdata:
            original = bdata.read()
            self.assertEqual(len(original), len(output))
            for i, x in enumerate(original):
                self.assertEqual(x, output[i], f'Wrong value at index {i}')

    def test_reverse_track_should_swap_waterfall_sides(self):
        (name, block, tri) = require_file('test/samples/AL1.TRI')
        tri = deepcopy(tri)
        length = len(tri['terrain']) * 4
        tri['road_spline'][100]['item_mode'] = 'waterfall_audio_left_channel'
        tri['road_spline'][200]['item_mode'] = 'waterfall_audio_right_channel'
        block.action_reverse_track(tri)
        self.assertEqual(tri['road_spline'][length - 1 - 100]['item_mode'], 'waterfall_audio_right_channel')
        self.assertEqual(tri['road_spline'][length - 1 - 200]['item_mode'], 'waterfall_audio_left_channel')


class TestNfs4FrdMap(unittest.TestCase):
    def test_nfs4_frd_should_be_same_size_and_stable(self):
        (name, block, data) = require_file('test/samples/GT1.FRD')
        with open('test/samples/GT1.FRD', 'rb') as bdata:
            original = bdata.read()
        output = block.pack(data, name=name)
        # `polygon_vroad_data.normal`/`.forward` are re-normalized to unit length on write, which
        # is lossy (the source data isn't always exactly unit length in the first place), so a
        # byte-identical round trip isn't expected here - only that the size is preserved and the
        # result stabilizes (a handful of vectors sit close enough to a quantization boundary that
        # convergence takes one extra cycle, hence comparing the 2nd and 3rd cycle rather than the
        # 1st and 2nd).
        self.assertEqual(len(original), len(output))
        data_twice = block.unpack_from_bytes(output, name=name + '__twice')
        output_twice = block.pack(data_twice, name=name + '__twice')
        data_thrice = block.unpack_from_bytes(output_twice, name=name + '__thrice')
        output_thrice = block.pack(data_thrice, name=name + '__thrice')
        self.assertEqual(output_twice, output_thrice)


class TestNfs6AiPaths(unittest.TestCase):
    def test_ai_paths_should_be_read_and_remain_the_same(self):
        import struct
        from resources.eac.maps.nfs6 import Nfs6AiPaths

        def graph(paths):
            nodes = [p for _, pts in paths for p in (pts[0], pts[-1])]
            b = struct.pack('<I', len(nodes)) + b''.join(struct.pack('<3f', *p) for p in nodes)
            b += struct.pack('<I', len(paths))
            for i, (name, pts) in enumerate(paths):
                b += name.encode().ljust(16, b'\0') + struct.pack('<IIfII', 2 * i, 2 * i + 1, 44.703, 1, len(pts))
                b += b''.join(struct.pack('<7f', *p, 10, -10, 1.5, 48) for p in pts)
            return b

        raw = struct.pack('<I', 1)
        raw += graph([('AI_center00', [(0, 1, 0), (0, 1, 5), (0, 1, 10)]), ('AI_center01', [(0, 1, 10), (5, 1, 10)])])
        raw += graph([('Helipath_center', [(0, 50, 0), (0, 50, 10)])])
        block = Nfs6AiPaths()
        data = block.unpack_from_bytes(raw)
        road = data['road_paths']
        self.assertEqual(len(road['nodes']), 4)
        self.assertEqual(road['paths'][1]['name'], 'AI_center01')
        self.assertEqual(road['paths'][1]['start_node'], 2)
        self.assertEqual(road['paths'][0]['points'][1]['position'], {'x': 0, 'y': 1, 'z': 5})
        self.assertEqual(road['paths'][0]['points'][1]['left_width'], 10)
        self.assertEqual(data['helicopter_paths']['paths'][0]['name'], 'Helipath_center')
        self.assertEqual(block.pack(data), raw)


class TestFrdMap(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.name, cls.block, cls.data = require_file('test/golden_corpus/TR00.FRD')

    def test_frd_should_remain_the_same(self):
        with open('test/golden_corpus/TR00.FRD', 'rb') as f:
            original = f.read()
        self.assertEqual(self.block.pack(self.data, name=self.name), original)

    def test_xobj_reference_point_should_match_block_reference(self):
        # pt_ref of an extra object is a float point, its reference in the block is 16.16 fixed point
        ref = self.data['blocks'][0]['xobj'][0]
        xobj = self.data['extraobject_blocks'][4 * 0][0]
        for k in 'xyz':
            self.assertAlmostEqual(ref['position'][k], xobj['data']['data']['pt_ref'][k], places=3)
        self.assertEqual(ref['position'], self.data['blocks'][0]['polyobj'][ref['cross_index']]['position'])

    def test_polyobj_references_should_follow_first_polyobj_chunk(self):
        refs = self.data['blocks'][0]['polyobj']
        objects = self.data['polygon_blocks'][0]['polyobj'][0]['data']['data']
        self.assertEqual([r['type'] for r in refs], [o['type'] for o in objects])
        self.assertEqual([r['size'] for r in refs], [20 if r['type'] == 4 else 16 for r in refs])
        self.assertEqual([r['xobj_idx'] for r in refs if r['type'] == 4], [0, 1, 2])
        self.assertEqual(len(self.data['blocks'][0]['polyobj_unused']), 4 * sum(1 for r in refs if r['type'] != 4))

    def test_animated_xobj_keyframes_should_have_unit_quaternions(self):
        animated = [x for chunk in self.data['extraobject_blocks'] for x in chunk if x['cross_type'] == 3]
        self.assertEqual(len(animated), 2)
        for xobj in animated:
            for frame in xobj['data']['data']['animdata']:
                q = frame['orientation']
                self.assertAlmostEqual(q['x'] ** 2 + q['y'] ** 2 + q['z'] ** 2 + q['w'] ** 2, 1, places=3)


class TestFrdPolyObjRef(unittest.TestCase):
    def test_record_size_should_depend_on_type(self):
        import struct
        from resources.eac.maps import FrdPolyObjRef

        block = FrdPolyObjRef()
        polygons = struct.pack('<HBB3i', 16, 1, 8, 65536, -65536, 32768)
        xobj = struct.pack('<HBB3iI', 20, 4, 5, 0, 0, 0, 2)
        data = block.unpack_from_bytes(polygons)
        self.assertEqual(data['position'], {'x': 1.0, 'y': -1.0, 'z': 0.5})
        self.assertEqual(block.pack(data), polygons)
        data = block.unpack_from_bytes(xobj)
        self.assertEqual(data['xobj_idx'], 2)
        self.assertEqual(block.pack(data), xobj)
        data['type'] = 1
        self.assertEqual(len(block.pack(data)), 16)


class TestMapColFile(unittest.TestCase):
    def test_col_files_should_remain_the_same(self):
        for path in ['test/golden_corpus/TR02.COL', 'test/golden_corpus/TR00.COL']:
            (name, block, data) = require_file(path)
            with open(path, 'rb') as f:
                self.assertEqual(block.pack(data, name=name), f.read(), path)

    def test_animated_prop_should_have_orientation(self):
        (_, _, data) = require_file('test/golden_corpus/TR02.COL')
        props = next(x for x in data['extrablocks'] if x['type'] == 'props_7')['data_records']['data']
        animated = [p for p in props if p['type'] == 'animated_prop']
        self.assertEqual(len(animated), 1)
        position = animated[0]['position']['data']
        self.assertEqual(position['anim_delay'], 44)
        q = position['frames'][0]['orientation']
        self.assertEqual((q['x'], q['z']), (0, 0))
        self.assertAlmostEqual(q['y'] ** 2 + q['w'] ** 2, 1, places=3)


class TestTrkMap(unittest.TestCase):
    def test_trk_should_remain_the_same_and_read_special_props(self):
        (name, block, data) = require_file('test/golden_corpus/TR02.TRK')
        with open('test/golden_corpus/TR02.TRK', 'rb') as f:
            self.assertEqual(block.pack(data, name=name), f.read())
        special = [
            p
            for sb in data['superblocks']
            for b in sb['blocks']
            for eb in b['extrablocks']
            if eb['type'] in ['props_7', 'props_18']
            for p in eb['data_records']['data']
            if p['type'] == 'special_prop'
        ]
        self.assertEqual(len(special), 34)
        self.assertEqual(special[0]['position']['data']['special_idx'], 0)
