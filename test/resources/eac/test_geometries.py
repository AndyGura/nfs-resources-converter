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


def build_eagl_model(index_padding=0xFFFF):
    """Minimal NFS6 EAGL model (MIPS ELF relocatable object): one render method with "ShadowTexture" shader (shadow
    map "0007", base texture "0042"), a quad of 4 vertices (FVF XYZ | DIFFUSE | TEX2) drawn as a triangle strip of 5
    indices, padded to 6 in the draw command"""
    import struct

    data = bytearray()
    relocations = []  # (offset in .data, symbol name, None for .data section symbol)
    symbols = []  # (name, value in .data or None for undefined)

    def align(n):
        while len(data) % n:
            data.append(0)

    # vertex buffer: position, diffuse BGRA, uv0 (base texture), uv1 (shadow map)
    vb = len(data)
    for x, z, u, v in [(0, 0, 0, 0), (1, 0, 2, 0), (0, 1, 0, 2), (1, 1, 2, 2)]:
        data += struct.pack('<3f', x, 5.0, z) + bytes([0x30, 0x20, 0x10, 0xFF]) + struct.pack('<4f', u, v, 0.5, 0.5)
    ib = len(data)
    data += struct.pack('<6H', 0, 0, 1, 2, 3, index_padding)
    align(4)
    tars = {}
    for name in ['0007', '0042']:
        tars[name] = len(data)
        symbols.append((f'__EAGL::TAR:::tar_{name}_1', len(data)))
        data += struct.pack('<I', 0) + name.encode() + bytes(40)
    geoprim = len(data)
    symbols.append(('__geoprimdatabuffer_0_1', geoprim))
    data += struct.pack('<I', 0)
    commands = len(data)
    data += struct.pack('<I', 0x04 << 16 | 12) + struct.pack(
        '<11I', 0, 32, 0x242, 0xFFFFFFFF, 0xFFFFFFFF, vb, 4, 0, 0, 0, 0
    )
    relocations.append((commands + 4 * 6, None))
    draw = len(data)
    data += struct.pack('<I', 0x07 << 16 | 6) + struct.pack('<5I', 2, 0xFFFFFFFF, 0xFFFFFFFF, ib, 6)
    relocations.append((draw + 4 * 4, None))
    data += struct.pack('<I', 0x11 << 16 | 1)
    rm = len(data)
    symbols.append(('__RenderMethod:::__GPRenderMethod_test_0', rm))
    data += struct.pack('<12I', commands, 0, 0, 0, 0, 0, 0, 0, 0, geoprim, 0, 0xABCDEFEA)
    relocations.append((rm, None))
    relocations.append((rm + 4 * 9, None))
    relocations.append((rm + 8, 'ShadowTexture__EAGLMicroCode'))
    # (count, pointer) parameters: textures, vertex buffer, index buffer with the real index count
    for count, pointer in [(1, tars['0007']), (1, tars['0042']), (4, vb), (5, ib)]:
        relocations.append((len(data) + 4, None))
        data += struct.pack('<2I', count, pointer)
    symbols.append(('__Model:::test', len(data)))
    data += bytes(16)
    symbols.append(('ShadowTexture__EAGLMicroCode', None))
    symbol_indices = {name: i + 2 for i, (name, _) in enumerate(symbols)}

    # string tables, symbol table (index 0 is null, index 1 is .data section symbol)
    shstrtab = b'\0.data\0.shstrtab\0.strtab\0.symtab\0.rel.data\0'
    strtab = b'\0'
    symtab = bytes(16) + struct.pack('<IIIBBH', 0, 0, 0, 3, 0, 1)
    for name, value in symbols:
        name_offset = len(strtab)
        strtab += name.encode() + b'\0'
        symtab += struct.pack(
            '<IIIBBH', name_offset, value or 0, 4 if value is not None else 0, 0x11, 0, 1 if value is not None else 0
        )
    reldata = b''.join(
        struct.pack('<II', offset, (symbol_indices[name] if name else 1) << 8 | 2) for offset, name in relocations
    )

    body = bytearray(bytes(12))  # .data is aligned to 16 bytes, header is 52 bytes long
    sections = []
    for name_offset, section_type, content, link, info, entry_size in [
        (1, 1, bytes(data), 0, 0, 0),
        (7, 3, shstrtab, 0, 0, 0),
        (17, 3, strtab, 0, 0, 0),
        (25, 2, symtab, 3, 2, 16),
        (33, 9, reldata, 4, 1, 8),
    ]:
        sections.append((name_offset, section_type, 52 + len(body), len(content), link, info, entry_size))
        body += content
        while len(body) % 4:
            body.append(0)
    header = (
        b'\x7fELF\x01\x01\x01\x00'
        + bytes(8)
        + struct.pack('<HHIIIIIHHHHHH', 1, 8, 1, 0, 0, 52 + len(body), 0, 52, 0, 0, 40, len(sections) + 1, 2)
    )
    section_headers = bytes(40) + b''.join(
        struct.pack('<10I', n, t, 0, 0, off, size, link, info, 4, es) for (n, t, off, size, link, info, es) in sections
    )
    return header + bytes(body) + section_headers


class TestEaglModel(unittest.TestCase):
    def test_eagl_model_should_remain_the_same(self):
        from resources.eac.geometries.nfs6 import EaglModel

        model = build_eagl_model()
        block = EaglModel()
        data = block.unpack_from_bytes(model)
        self.assertEqual(data['machine'], 8)
        self.assertEqual(len(data['section_headers']), 6)
        self.assertEqual(block.pack(data), model)

    def test_eagl_meshes_should_be_read(self):
        from resources.eac.geometries.nfs6 import EaglModel, read_eagl_meshes, eagl_model_name

        data = EaglModel().unpack_from_bytes(build_eagl_model())
        self.assertEqual(eagl_model_name(data), 'test')
        meshes = read_eagl_meshes(data)
        self.assertEqual(len(meshes), 1)
        mesh = meshes[0]
        self.assertEqual(mesh.shader, 'ShadowTexture')
        self.assertListEqual(mesh.textures, ['0007', '0042'])
        # the first texture of shadow shaders is a shadow map, the base texture uses the first UV set
        self.assertEqual(mesh.main_texture, '0042')
        self.assertListEqual(mesh.main_uvs, [(0, 0), (2, 0), (0, 2), (2, 2)])
        self.assertListEqual(mesh.vertices, [(0, 5, 0), (1, 5, 0), (0, 5, 1), (1, 5, 1)])
        self.assertListEqual(mesh.colors, [0x102030FF] * 4)
        # strip 0 0 1 2 3: degenerate triangle skipped, odd triangles flipped; padding index not drawn even if valid
        self.assertListEqual(mesh.triangles, [(1, 0, 2), (1, 2, 3)])
        self.assertListEqual(
            read_eagl_meshes(EaglModel().unpack_from_bytes(build_eagl_model(index_padding=0)))[0].triangles,
            [(1, 0, 2), (1, 2, 3)],
        )
