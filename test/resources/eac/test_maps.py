import unittest

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
