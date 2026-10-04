import struct
import unittest

from library import require_file

VERTICES_CHUNK_ID = 0x00_13_4B_01


def _find_chunk_path(data: bytes, chunk_id: int, start=0, end=None):
    # returns offsets of all chunk headers from the top level down to the first chunk with the given id
    end = len(data) if end is None else end
    offset = start
    while offset + 8 <= end:
        cid, length = struct.unpack_from('<II', data, offset)
        if cid == chunk_id:
            return [offset]
        if cid & 0x80_00_00_00:
            sub_path = _find_chunk_path(data, chunk_id, offset + 8, offset + 8 + length)
            if sub_path:
                return [offset] + sub_path
        offset += 8 + length
    return None


def _strip_normals_from_first_mesh(data: bytes):
    # rewrites the first vertices chunk of the file from 36-byte vertices to 24-byte vertices without normal,
    # fixing lengths of all parent container chunks, the way such meshes are stored in the game files
    path = _find_chunk_path(data, VERTICES_CHUNK_ID)
    offset = path[-1]
    length = struct.unpack_from('<I', data, offset + 4)[0]
    payload = data[offset + 8 : offset + 8 + length]
    elevens_amount = len(payload) - len(payload.lstrip(b'\x11'))
    assert (len(payload) - elevens_amount) % 36 == 0
    elevens, raw_vertices = payload[:elevens_amount], payload[elevens_amount:]
    vertices = [raw_vertices[i : i + 36] for i in range(0, len(raw_vertices), 36)]
    new_payload = elevens + b''.join(v[:12] + v[24:] for v in vertices)
    delta = len(new_payload) - len(payload)
    res = bytearray(data[: offset + 8] + new_payload + data[offset + 8 + length :])
    for chunk_offset in path:
        struct.pack_into('<I', res, chunk_offset + 4, struct.unpack_from('<I', res, chunk_offset + 4)[0] + delta)
    return bytes(res), vertices


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

    def test_mesh_with_24_byte_vertices_should_be_read_and_remain_the_same(self):
        (name, block, _) = require_file('test/samples/GEOMETRY.BIN')
        with open('test/samples/GEOMETRY.BIN', 'rb') as bdata:
            original = bdata.read()
        modified, original_vertices = _strip_normals_from_first_mesh(original)

        data = block.unpack_from_bytes(modified, name=name + '__24')
        chunk = next(_vertices_chunks(data))
        self.assertEqual(chunk['vertices']['choice_index'], 1)
        self.assertEqual(len(chunk['vertices']['data']), len(original_vertices))
        for vertex, raw in zip(chunk['vertices']['data'], original_vertices):
            self.assertEqual(
                [vertex['position']['x'], vertex['position']['y'], vertex['position']['z']],
                list(struct.unpack_from('<3f', raw, 0)),
            )
            self.assertEqual(vertex['unk3'], struct.unpack_from('<I', raw, 24)[0])
            self.assertEqual([vertex['u'], vertex['v']], list(struct.unpack_from('<2f', raw, 28)))
        self.assertTrue(all(c['vertices']['choice_index'] == 0 for c in list(_vertices_chunks(data))[1:]))

        self.assertEqual(modified, block.pack(data, name=name + '__24'))
