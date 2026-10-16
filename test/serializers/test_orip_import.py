import os
import shutil
import tempfile
import unittest
from collections import Counter

from PIL import Image

from library import require_file, require_resource
from library.exceptions import DataIntegrityException
from serializers import OripGeometrySerializer
from serializers.geometries import orip_polygon_partitions

ORIP_ID = '{}__children/{}/item/data'


def canonical_polygons(data: dict) -> Counter:
    """Polygons as the game draws them, whatever their order and the order of the vertices and tables: type, texture
    coordinates, winding (a flipped polygon is its reverse), material, labels and partition"""
    vertices = data['vertices']['data']
    partitions = orip_polygon_partitions(data)
    result = Counter()
    for pi, polygon in enumerate(data['polygons']):
        n = polygon['polygon_type'] & 7
        mapping = polygon['mapping']
        positions = [tuple(vertices[data['vmap'][polygon['offset_3d'] + k]].values()) for k in range(n)]
        if mapping['use_uv']:
            uvs = [tuple(data['vertex_uvs'][data['vmap'][polygon['offset_2d'] + k]].values()) for k in range(n)]
            cycle = list(zip(positions, uvs))
            if mapping['flip_normal']:
                cycle = cycle[::-1]

            def rotated(c):
                return min(tuple(c[j:] + c[:j]) for j in range(len(c)))

            geometry = min(rotated(cycle), rotated(cycle[::-1])) if mapping['two_sided'] else rotated(cycle)
        else:
            # without UVs the texture corners follow the vertex order
            geometry = (tuple(positions), mapping['two_sided'] or mapping['flip_normal'])
        material = data['materials'][polygon['material_index']]
        labels = tuple(sorted(x['name'] for x in data['labels'] if x['index'] == pi))
        result[
            (
                polygon['polygon_type'],
                mapping['two_sided'],
                geometry,
                material['name'],
                material['file_name'],
                material['color'],
                labels,
                partitions[pi],
            )
        ] += 1
    return result


def named_points(data: dict) -> list:
    vertices = data['vertices']['data']
    return sorted((x['name'], tuple(vertices[x['index']].values())) for x in data['fx_polys'])


def morph_deltas(data: dict) -> dict:
    vertices = data['vertices']['data']
    return {
        m['name']: sorted(
            (
                tuple(vertices[data['vmap'][m['vmap_offset'] + i]].values()),
                tuple(vertices[m['first_delta'] + i].values()),
            )
            for i in range(m['num_vertices'])
        )
        for m in data['morphs']
    }


def export_and_import(file_path: str, index: int):
    """(ORIP data, ORIP imported from its own export, import report)"""
    file_id, _, _ = require_file(file_path)
    orip_id = ORIP_ID.format(file_id, index)
    (_, block, data), _ = require_resource(orip_id)
    serializer = OripGeometrySerializer()
    serializer.patch_settings(serializer.ui_serialization()['reversible_settings_patch'])
    with tempfile.TemporaryDirectory() as tmp:
        serializer.serialize(data, tmp + '/', orip_id, block)
        imported = serializer.deserialize([tmp], orip_id, block)
    return data, imported, serializer.deserialize_report


def import_obj(obj: str, mtl: str = '', files: dict = None, index: int = 0):
    """ORIP imported from the OBJ text over ORIP `index` of TSUPRA.CFM, with the report"""
    file_id, _, _ = require_file('test/samples/TSUPRA.CFM')
    orip_id = ORIP_ID.format(file_id, index)
    (_, block, _), _ = require_resource(orip_id)
    serializer = OripGeometrySerializer()
    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(tmp, 'model.obj'), 'w') as f:
            f.write(('mtllib model.mtl\n' if mtl else '') + obj)
        if mtl:
            with open(os.path.join(tmp, 'model.mtl'), 'w') as f:
                f.write(mtl)
        for name, image in (files or {}).items():
            image.save(os.path.join(tmp, name))
        imported = serializer.deserialize([tmp], orip_id, block)
    return imported, serializer.deserialize_report


def quad(v0, v1, v2, v3, with_uvs=True):
    """OBJ lines of a quad face, in ORIP axes (x, y up, z forward), written in OBJ axes (y and z swapped) as the
    export does"""
    lines = [f'v {x} {z} {y}' for x, y, z in (v0, v1, v2, v3)]
    if with_uvs:
        lines += ['vt 0.25 0.75', 'vt 0.5 0.75', 'vt 0.5 0.5', 'vt 0.25 0.5']
        lines.append('f -4/-4 -3/-3 -2/-2 -1/-1')
    else:
        lines.append('f -4 -3 -2 -1')
    return '\n'.join(lines) + '\n'


def wheel(label, x, z):
    return f'o lbl__{label}\n' + quad((x, 0.7, z + 0.35), (x, 0.7, z - 0.35), (x, 0, z - 0.35), (x, 0, z + 0.35), False)


class TestOripImportRoundTrip(unittest.TestCase):
    def test_car_model_export_imports_back(self):
        for index in (0, 2):
            with self.subTest(index=index):
                data, imported, report = export_and_import('test/samples/TSUPRA.CFM', index)
                self.assertEqual(canonical_polygons(imported), canonical_polygons(data))
                self.assertEqual(named_points(imported), named_points(data))
                self.assertEqual(morph_deltas(imported), morph_deltas(data))
                self.assertEqual(len(imported['vertex_uvs']), len(data['vertex_uvs']))
                self.assertEqual([p['name'] for p in imported['partitions']], [p['name'] for p in data['partitions']])
                self.assertNotIn('textures not in the FSH', report)

    def test_lookup_only_materials_are_kept(self):
        data, imported, _ = export_and_import('test/samples/TSUPRA.CFM', 0)
        names = {m['name'].rstrip(b'\0') for m in imported['materials']}
        self.assertTrue({b'tire1', b'tire2', b'tire3', b'tire4', b'pal', b'frntires', b'rertires'} <= names)

    def test_imported_model_is_saved_and_read_back(self):
        file_id, block, data = require_file('test/samples/TSUPRA.CFM', lazy=False)
        _, imported, _ = export_and_import('test/samples/TSUPRA.CFM', 0)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'TSUPRA.CFM')
            children = list(data['children'])
            children[0] = {**children[0], 'item': {**children[0]['item'], 'data': imported}}
            with open(path, 'wb') as f:
                f.write(block.pack({**data, 'children': children}, name='TSUPRA.CFM'))
            _, _, read = require_file(path, lazy=False)
            self.assertEqual(canonical_polygons(read['children'][0]['item']['data']), canonical_polygons(imported))
            self.assertEqual(read['children'][1], data['children'][1])

    def test_track_prop_vertices_are_32_4(self):
        # a FAM holds props with the vertex format of every ORIP but a CFM's: the file name decides
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'PROPS.FAM')
            shutil.copy('test/samples/TSUPRA.CFM', path)
            data, imported, _ = export_and_import(path, 2)
            self.assertEqual(imported['vertices']['choice_index'], 1)
            self.assertEqual(canonical_polygons(imported), canonical_polygons(data))
            self.assertTrue(all((v['x'] * 16).is_integer() for v in imported['vertices']['data']))


class TestOripImportFromEditor(unittest.TestCase):
    WHEELS = (
        wheel('lt_frnt', -0.9, 1.3)
        + wheel('rt_frnt', 0.9, 1.3)
        + wheel('lt_rear', -0.9, -1.3)
        + wheel('rt_rear', 0.9, -1.3)
        + 'o circ\nusemtl circ\n'
        + quad((-0.6, 0.7, 1.65), (-0.6, 0.7, 0.95), (-0.6, 0, 0.95), (-0.6, 0, 1.65), False)
        + quad((0.6, 0.7, 1.65), (0.6, 0.7, 0.95), (0.6, 0, 0.95), (0.6, 0, 1.65), False)
    )
    BODY = 'o body\nusemtl topv\n' + quad((-0.8, 1, 2), (0.8, 1, 2), (0.8, 1, -2), (-0.8, 1, -2))
    MTL = 'newmtl topv\nmap_Kd assets/topv.png\n\nnewmtl circ\nmap_Kd assets/circ.png\n'

    def test_quads_labels_and_partitions(self):
        data, report = import_obj(self.WHEELS + self.BODY, self.MTL)
        self.assertEqual(len(data['polygons']), 7)
        self.assertTrue(all(p['polygon_type'] & 7 == 4 for p in data['polygons']))
        self.assertEqual(sorted(x['name'] for x in data['labels']), ['lt_frnt', 'lt_rear', 'rt_frnt', 'rt_rear'])
        partitions = {p['name']: p['num_polygons'] for p in data['partitions']}
        # wheel quads outside, the body (unknown mesh name) on the surface, circ like the current circ quads
        self.assertEqual(partitions, {'NON-SORT': 0, 'inside': 2, 'surface': 1, 'outside': 4})
        wheel_material = data['materials'][data['polygons'][0]['material_index']]
        self.assertEqual(wheel_material['name'].rstrip(b'\0'), b'frntires')
        self.assertEqual(data['polygons'][0]['polygon_type'], 0x8C)
        self.assertNotIn('textures not in the FSH', report)

    def test_texture_coordinates_in_texels_of_the_fsh_bitmap(self):
        data, _ = import_obj(self.BODY, self.MTL)
        body = data['polygons'][0]
        self.assertTrue(body['mapping']['use_uv'])
        uvs = [data['vertex_uvs'][data['vmap'][body['offset_2d'] + k]] for k in range(4)]
        file_id, _, _ = require_file('test/samples/TSUPRA.CFM')
        (_, _, topv), _ = require_resource(f'{file_id}__children/1/item/data')
        size = next(c['item']['data'] for c in topv['children'] if c['alias'] == 'topv')
        width, height = size['width'], size['height']
        self.assertEqual(uvs[0], {'u': round(width / 4), 'v': round(height / 4)})
        self.assertEqual(uvs[2], {'u': round(width / 2), 'v': round(height / 2)})

    def test_wheel_points_follow_the_wheels(self):
        data, _ = import_obj(self.WHEELS + self.BODY, self.MTL)
        points = dict(named_points(data))
        self.assertEqual(points['FL0'], (-0.8984375, 0.0, 1.6484375))
        self.assertEqual(points['FL1'], (-0.8984375, 0.0, 0.953125))
        self.assertEqual(points['RR1'], (0.8984375, 0.0, -1.6484375))
        # not on the geometry: stays where it is in the current model, as a vertex of its own
        (_, _, current), _ = require_resource(ORIP_ID.format(require_file('test/samples/TSUPRA.CFM')[0], 0))
        self.assertEqual(points['smok'], dict(named_points(current))['smok'])

    def test_wheel_morphs_are_made_for_moved_wheels(self):
        data, report = import_obj(self.WHEELS + self.BODY, self.MTL)
        self.assertIn('morph left_tur made again', report)
        morphs = morph_deltas(data)
        self.assertEqual(len(morphs['left_tur']), 8)
        self.assertEqual(len(morphs['right_tu']), 8)
        # the front edge of the left wheel quad goes left (-x) when the wheel turns left
        front = [d for v, d in morphs['left_tur'] if v[0] < -0.8 and v[2] > 1.5]
        self.assertTrue(front and all(d[0] < 0 for d in front))
        self.assertTrue(all(d[1] == 0 for _, deltas in morphs.items() for _, d in deltas))

    def test_flat_colour_material(self):
        data, _ = import_obj(
            'usemtl red\n' + quad((0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)), 'newmtl red\nKd 1 0 0\n'
        )
        polygon = data['polygons'][0]
        self.assertEqual(polygon['polygon_type'], 0x04)
        self.assertEqual(data['materials'][polygon['material_index']]['color'], 0xFF0000)

    def test_new_texture_takes_the_size_of_its_image(self):
        image = Image.new('RGBA', (8, 4), (255, 0, 0, 0))
        data, report = import_obj(
            'usemtl new_one\n' + quad((0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)),
            'newmtl new_one\nmap_Kd door.png\n',
            {'door.png': image},
        )
        polygon = data['polygons'][0]
        self.assertEqual(data['materials'][polygon['material_index']]['file_name'], 'door')
        # transparent texels: colour-keyed
        self.assertEqual(polygon['polygon_type'], 0x8C)
        self.assertEqual(data['vertex_uvs'][data['vmap'][polygon['offset_2d']]], {'u': 2, 'v': 1})
        self.assertIn('textures not in the FSH: door', report)

    def test_triangles_of_a_quad_and_two_sided_faces(self):
        obj = (
            'usemtl topv\n'
            'v 0 0 0\nv 1 0 0\nv 1 0 1\nv 0 0 1\nvt 0 0\nvt 0.5 0\nvt 0.5 0.5\nvt 0 0.5\n'
            'f 1/1 2/2 3/3\nf 1/1 3/3 4/4\nf 1/1 3/3 2/2\nf 1/1 4/4 3/3\n'
        )
        data, _ = import_obj(obj, self.MTL)
        self.assertEqual(len(data['polygons']), 1)
        self.assertEqual(data['polygons'][0]['polygon_type'] & 7, 4)
        self.assertTrue(data['polygons'][0]['mapping']['two_sided'])

    def test_bigger_faces_are_split_into_triangles(self):
        obj = 'v 0 0 0\nv 1 0 0\nv 2 0 1\nv 1 0 2\nv 0 0 1\nf 1 2 3 4 5\n'
        data, _ = import_obj(obj)
        self.assertEqual([p['polygon_type'] & 7 for p in data['polygons']], [3, 3, 3])

    def test_materials_must_be_named_after_bitmaps(self):
        with self.assertRaises(DataIntegrityException):
            import_obj(
                'usemtl Material.001\n' + quad((0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)), 'newmtl Material.001\n'
            )
