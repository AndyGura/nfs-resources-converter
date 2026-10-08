import json
import math
import os
import re
import shutil
import tempfile
import unittest
from configparser import ConfigParser

from PIL import Image

from serializers.geometries import (
    compose_texture_page,
    crp_car_default_style,
    crp_car_is_image_used,
    crp_car_texture_page_sources,
    crp_image_atlas_position,
    texture_alpha_mode,
)


class TestCrpImageAtlasPosition(unittest.TestCase):
    def test_reads_12_lower_bits(self):
        self.assertEqual(crp_image_atlas_position({'position': {'x': 192, 'y': 64}}), (192, 64))

    def test_ignores_flags_in_higher_bits(self):
        self.assertEqual(crp_image_atlas_position({'position': {'x': 0, 'y': 0x7000}}), (0, 0))

    def test_values_are_signed(self):
        self.assertEqual(crp_image_atlas_position({'position': {'x': 191, 'y': 0xFFFF}}), (191, -1))


class TestComposeTexturePage(unittest.TestCase):
    def test_size_is_rounded_up_to_power_of_two(self):
        page = compose_texture_page([(Image.new('RGBA', (64, 16)), 100, 20)])
        self.assertEqual(page.size, (256, 64))

    def test_explicit_size(self):
        page = compose_texture_page([(Image.new('RGBA', (16, 16)), 0, 0)], 128, 32)
        self.assertEqual(page.size, (128, 32))

    def test_places_images_and_first_one_wins_on_overlap(self):
        red = Image.new('RGBA', (16, 16), (255, 0, 0, 255))
        green = Image.new('RGBA', (16, 16), (0, 255, 0, 255))
        blue = Image.new('RGBA', (16, 16), (0, 0, 255, 255))
        page = compose_texture_page([(red, 0, 0), (green, 0, 0), (blue, 16, 0)])
        self.assertEqual(page.size, (32, 16))
        self.assertEqual(page.getpixel((5, 5)), (255, 0, 0, 255))
        self.assertEqual(page.getpixel((20, 5)), (0, 0, 255, 255))


class TestTextureAlphaMode(unittest.TestCase):
    def test_opaque_and_masked_textures_are_cutout(self):
        image = Image.new('RGBA', (16, 16), (255, 0, 0, 255))
        image.paste((0, 0, 0, 0), (0, 0, 8, 16))
        self.assertEqual(texture_alpha_mode(image), 'cutout')

    def test_anti_aliased_edges_are_cutout(self):
        image = Image.new('RGBA', (16, 16), (255, 0, 0, 255))
        image.paste((255, 0, 0, 128), (0, 0, 1, 16))
        self.assertEqual(texture_alpha_mode(image), 'cutout')

    def test_partial_alpha_is_blend(self):
        image = Image.new('RGBA', (16, 16), (255, 0, 0, 255))
        image.paste((255, 0, 0, 128), (0, 0, 4, 16))
        self.assertEqual(texture_alpha_mode(image), 'blend')


class TestCrpCarTexturePageSources(unittest.TestCase):
    def test_default_layout(self):
        self.assertEqual(
            crp_car_texture_page_sources([0, 1, 2, 3, 7]),
            {0: 0, 1: 0, 2: 1, 3: 2, 4: 3, 8: 7},
        )

    def test_layout_from_tpg(self):
        tpg = ConfigParser(strict=False)
        tpg.read_string(
            """
[tpage1.details]
mirrortpage=2
[tpage2.details]
sourcetpage=1
[file1.details]
tpage=1
[file2.details]
tpage=4
[file3.details]
tpage=3
"""
        )
        self.assertEqual(crp_car_texture_page_sources([0, 1, 2], tpg), {0: 0, 1: 0, 3: 1, 2: 2})


class TestCrpCarStyle(unittest.TestCase):
    def setUp(self):
        self.tpg = ConfigParser(strict=False, interpolation=None)
        self.tpg.read_string(
            """
[style2]
geometry1=8
type1=1
[style1]
geometry1=8
type1=3
texture2=4
type2=1
[file1.top]
geometry1=8
type1=0
[file1.top1]
geometry1=8
type1=3
geometry2=8
type2=4
[file1.dec]
texture1=4
type1=1
racedecal=1
[file1.fro]
frontend=0
"""
        )

    def test_default_style_is_lowest_numbered(self):
        self.assertEqual(crp_car_default_style(self.tpg), {('geometry', 8): 3, ('texture', 4): 1})

    def test_no_styles(self):
        self.assertEqual(crp_car_default_style(ConfigParser()), {})

    def test_image_selection(self):
        style = crp_car_default_style(self.tpg)
        self.assertFalse(crp_car_is_image_used(self.tpg, 1, 'top', style))
        self.assertTrue(crp_car_is_image_used(self.tpg, 1, 'top1', style))
        self.assertFalse(crp_car_is_image_used(self.tpg, 1, 'dec', style))
        self.assertFalse(crp_car_is_image_used(self.tpg, 1, 'fro', style))
        self.assertTrue(crp_car_is_image_used(self.tpg, 1, 'sid', style))
        self.assertTrue(crp_car_is_image_used(self.tpg, 1, 'top', {}))


class TestCrpGeometrySerializer(unittest.TestCase):
    def _serialize(self, file_path, out):
        from library import require_file
        from serializers import get_serializer

        name, block, data = require_file(file_path)
        serializer = get_serializer(block, data)
        serializer.patch_settings(
            {'geometry__save_obj': True, 'geometry__save_blend': False, 'geometry__export_to_gg_web_engine': False}
        )
        serializer.serialize(data, out, id=name, block=block)

    def test_car_meshes_get_texture_pages(self):
        with tempfile.TemporaryDirectory() as out:
            self._serialize('test/samples/356b.crp', out)
            # wheel and window materials keep the alpha channel, other pages are opaque
            for page, size in [('0', 256), ('1', 256), ('2', 256), ('3', 128), ('3_alpha', 128), ('4_alpha', 64)]:
                with Image.open(os.path.join(out, 'textures', f'page_{page}.png')) as img:
                    self.assertEqual(img.size, (size, size))
            with open(os.path.join(out, 'material.mtl')) as f:
                mtl = f.read()
            self.assertEqual(
                re.findall(r'newmtl (\S+)', mtl),
                ['page_0', 'page_1', 'page_2', 'page_3', 'page_3_alpha', 'page_4_alpha'],
            )
            # only glass is translucent
            self.assertEqual(
                re.findall(r'alpha_mode (\S+)', mtl), ['cutout', 'cutout', 'cutout', 'cutout', 'cutout', 'blend']
            )
            with open(os.path.join(out, 'geometry.obj')) as f:
                obj = f.read()
            body_meshes = re.findall(r'\no (Body_LOD1_ai0[^\n]*)\n', obj)
            self.assertIn('Body_LOD1_ai0_page_0', body_meshes)
            self.assertIn('Body_LOD1_ai0_page_0_damaged', body_meshes)
            self.assertIn('usemtl page_0', obj)
            # triangle part without vertex index row
            self.assertIn('\no DecalDoorL_LOD6_ai0_page_0\n', obj)

    def test_malformed_tpg_falls_back_to_default_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            # directory name has characters which are special in resource ids
            car_dir = os.path.join(tmp, 'my__cars')
            os.makedirs(car_dir)
            shutil.copy('test/samples/356b.crp', car_dir)
            with open(os.path.join(car_dir, '356b.tpg'), 'w') as f:
                f.write('[tpage1.details]\nwidth=256.0\nheight=256\n[file1.details]\ntpage=\n')
            out = os.path.join(tmp, 'out')
            self._serialize(os.path.join(car_dir, '356b.crp'), out)
            with open(os.path.join(out, 'material.mtl')) as f:
                self.assertEqual(
                    re.findall(r'newmtl (\S+)', f.read()),
                    ['page_0', 'page_1', 'page_2', 'page_3', 'page_3_alpha', 'page_4_alpha'],
                )

    @unittest.skipUnless(os.path.exists('test/samples/alps.crp'), 'needs NFS5 track sample test/samples/alps.crp')
    def test_track_chunks_for_track_viewer(self):
        from library import require_resource
        from library.utils.id import join_id
        from serializers import get_serializer

        (_, block, data), _ = require_resource(join_id('test/samples/alps.crp', 'data'))
        serializer = get_serializer(block, data)
        serializer.patch_settings(
            {
                'geometry__save_obj': True,
                'geometry__save_blend': False,
                'geometry__export_to_gg_web_engine': False,
                'maps__save_as_chunked': True,
            }
        )
        try:
            with tempfile.TemporaryDirectory() as out:
                files = serializer.serialize(data, out, id=join_id('test/samples/alps.crp', 'data'), block=block)
                with open(os.path.join(out, 'track_layout.json')) as f:
                    layout = json.load(f)
                # one chunk per road piece of the main road: RD0000C..RD1792C, every 8th
                self.assertEqual(len(layout['chunks']), 225)
                self.assertFalse(layout['closed'])
                self.assertEqual(len([x for x in files if x.endswith('.obj')]), 225)
                # the first road piece goes from Z=464 to Z=416
                self.assertAlmostEqual(layout['chunks'][0]['position']['z'], 464, delta=5)
                self.assertAlmostEqual(abs(layout['chunks'][0]['orientation']), math.pi, delta=0.1)
                with open(os.path.join(out, 'terrain_chunk_0.obj')) as f:
                    obj = f.read()
                # LOD 0 only, material is the FSH alias after the last "_"
                self.assertNotIn('LOD1', obj)
                self.assertIn('\no terrain_chunk_0_0_cla2\n', obj)
                self.assertNotIn('mtllib', obj)
                # pivoted at the road piece center
                xs = [float(line.split()[1]) for line in obj.splitlines() if line.startswith('v ')]
                self.assertLess(max(abs(x) for x in xs), 200)
        finally:
            serializer.patch_settings({'maps__save_as_chunked': False})


class TestFce3GeometrySerializer(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    def _serialize_car_viv(self, build_data=None, fce_name='car.fce', textures=None):
        from io import BytesIO

        from library import require_resource
        from library.loader import clear_file_cache, path_to_name
        from resources.eac.archives import BigfBlock
        from serializers import get_serializer
        from test.resources.eac.test_geometries import build_fce3_data

        fce_block, fce_data = (build_data or build_fce3_data)()
        tga_items = []
        for alias, color in textures or [('car00.tga', (255, 0, 0, 0))]:
            tga = BytesIO()
            Image.new('RGBA', (4, 4), color).save(tga, format='TGA')
            tga_items.append((alias, tga.getvalue()))
        bigf = BigfBlock()
        bigf_data = bigf.new_data()
        bytes_choice = bigf.item_block.get_choice_index_by_class_name('BytesBlock')
        bigf_data['children'] = [
            {
                'alias': alias,
                'item': {'choice_index': bytes_choice, 'data': item_bytes},
                'pre_offset_payload': b'',
                'post_offset_payload': b'',
            }
            for alias, item_bytes in [(fce_name, fce_block.pack(fce_data))] + tga_items
        ]
        viv_path = os.path.join(self.tmp_dir, 'car.viv')
        with open(viv_path, 'wb') as f:
            f.write(bigf.pack(bigf_data))
        clear_file_cache(viv_path)
        fce_id = path_to_name(viv_path) + '__children/0/item/data'
        (fce_id, block, data), _ = require_resource(fce_id)
        self.assertEqual(block.__class__, fce_block.__class__)
        serializer = get_serializer(block, data)
        serializer.patch_settings(
            {'geometry__save_obj': True, 'geometry__save_blend': False, 'geometry__export_to_gg_web_engine': False}
        )
        out_path = os.path.join(self.tmp_dir, 'out/')
        serializer.serialize(data, out_path, id=fce_id, block=block)
        return out_path

    def test_exports_parts_with_texture(self):
        out_path = self._serialize_car_viv()
        with open(os.path.join(out_path, 'geometry.obj')) as f:
            obj = f.read()
        with open(os.path.join(out_path, 'material.mtl')) as f:
            mtl = f.read()
        objects = re.findall(r'^o (.*)$', obj, re.MULTILINE)
        self.assertEqual(objects, ['hp_0_HB__car00', 'hp_1_HLFW__car00_translucent'])
        self.assertIn('map_Kd assets/car00.png', mtl)
        self.assertIn('newmtl car00_translucent', mtl)
        self.assertIn('alpha_mode blend', mtl)
        # alpha channel of car texture is not transparency
        with Image.open(os.path.join(out_path, 'assets/car00.png')) as png:
            self.assertEqual(png.convert('RGBA').getpixel((0, 0)), (255, 0, 0, 255))
        with Image.open(os.path.join(out_path, 'assets/car00_paint_mask.png')) as png:
            self.assertEqual(png.convert('RGBA').getpixel((0, 0)), (255, 0, 0, 0))
        # vertices are shared by triangle corners with the same UV: quad has 5 of them (vertex 2 has different UV in
        # both triangles). Double-sided triangle has 3 vertices and 2 faces
        self.assertEqual(len(re.findall(r'^v ', obj, re.MULTILINE)), 8)
        self.assertEqual(len(re.findall(r'^f ', obj, re.MULTILINE)), 4)
        # part position is applied, axes: (x, z, y)
        self.assertIn('v 1.0 4.0 2.0', obj)
        # V goes from bottom to top, as in OBJ
        self.assertIn('vt 0.0 0.25', obj)

    def test_exports_dummies(self):
        out_path = self._serialize_car_viv()
        import json

        with open(os.path.join(out_path, 'geometry_extra.json')) as f:
            extra = json.load(f)
        self.assertEqual(extra['dummies'], [{'name': 'HFLO', 'position': [0.5, 2.0, 0.25]}])


class TestFce4GeometrySerializer(unittest.TestCase):
    setUp = TestFce3GeometrySerializer.setUp
    tearDown = TestFce3GeometrySerializer.tearDown
    _serialize_car_viv = TestFce3GeometrySerializer._serialize_car_viv

    def test_exports_damaged_copy_of_parts(self):
        from test.resources.eac.test_geometries import build_fce4_data

        out_path = self._serialize_car_viv(build_fce4_data)
        with open(os.path.join(out_path, 'geometry.obj')) as f:
            obj = f.read()
        objects = re.findall(r'^o (.*)$', obj, re.MULTILINE)
        self.assertEqual(
            objects, ['hp_0_HB__car00', 'hp_0_HB__car00_damaged', 'hp_1_HLFW__car00', 'hp_1_HLFW__car00_damaged']
        )
        # damaged position of vertex 2 (x, z, y)
        self.assertIn('v 0.75 -0.5 0.75', obj)
        # V goes from top to bottom, OBJ has it from bottom to top
        self.assertIn('vt 0.0 0.75', obj)

    def test_part_lod_prefix(self):
        from serializers.geometries import fce4_part_lod_prefix

        self.assertEqual(
            [fce4_part_lod_prefix(x) for x in [':HB', ':MRFW', ':LB', ':TB', ':OD', ':ORM', 'body']],
            ['hp', 'mp', 'lp', 'tp', 'hp', 'hp', 'part'],
        )

    def test_upgrade_model_uses_own_texture(self):
        from test.resources.eac.test_geometries import build_fce4_data

        out_path = self._serialize_car_viv(
            build_fce4_data,
            fce_name='car1.fce',
            textures=[('car00.tga', (255, 0, 0, 223)), ('car100.tga', (0, 255, 0, 0))],
        )
        with open(os.path.join(out_path, 'material.mtl')) as f:
            mtl = f.read()
        self.assertIn('map_Kd assets/car100.png', mtl)
        self.assertNotIn('car00', mtl)
        # alpha 0 is transparency
        with Image.open(os.path.join(out_path, 'assets/car100.png')) as png:
            self.assertEqual(png.convert('RGBA').getpixel((0, 0)), (0, 255, 0, 0))
        with open(os.path.join(out_path, 'geometry.obj')) as f:
            # car1.fce is a car model too: part roles by name
            self.assertIn('o hp_0_HB__car100\n', f.read())


NFS6_CAR_SAMPLE_DIR = 'test/samples/claude_tmp/nfs6_car'


class TestNfs6CarSerializer(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    def _serialize(self, model_id):
        from library import require_resource
        from serializers import get_serializer

        (model_id, block, data), _ = require_resource(model_id)
        serializer = get_serializer(block, data)
        serializer.patch_settings(
            {'geometry__save_obj': True, 'geometry__save_blend': False, 'geometry__export_to_gg_web_engine': False}
        )
        out_path = os.path.join(self.tmp_dir, 'out/')
        paths = serializer.serialize(data, out_path, id=model_id, block=block)
        return out_path, paths

    def test_car_model_without_textures(self):
        from library.loader import clear_file_cache, path_to_name
        from test.resources.eac.test_geometries import build_eagl_model

        path = os.path.join(self.tmp_dir, 'car.o')
        with open(path, 'wb') as f:
            f.write(build_eagl_model(car=True))
        clear_file_cache(path)
        out_path, paths = self._serialize(path_to_name(path))
        self.assertTrue(any(x.endswith('skins.json') for x in paths))
        with open(os.path.join(out_path, 'geometry.obj')) as f:
            obj = f.read()
        self.assertEqual(re.findall(r'^o (.*)$', obj, re.MULTILINE), ['hp_0_ALPHA_OPAQUE_HOODShape'])
        # game (x, y, z) -> (x, -z, y): Y up, front at -Z becomes Z up, front at +Y
        self.assertIn('v 1.0 -1.0 5.0', obj)
        # rotation keeps handedness, so faces keep facing outwards: winding of every triangle is reversed back
        faces = re.findall(r'^f (\d+)/\d+ (\d+)/\d+ (\d+)/\d+$', obj, re.MULTILINE)
        self.assertEqual(faces, [('3', '1', '2'), ('4', '3', '2')])

    @unittest.skipUnless(os.path.exists(NFS6_CAR_SAMPLE_DIR), f'needs NFS6 car sample {NFS6_CAR_SAMPLE_DIR}')
    def test_car_from_car_viv(self):
        out_path, _ = self._serialize(f'{NFS6_CAR_SAMPLE_DIR}/car.viv__children/2/item/data')
        with open(os.path.join(out_path, 'geometry.obj')) as f:
            objects = re.findall(r'^o (.*)$', f.read(), re.MULTILINE)
        self.assertEqual(len(objects), 31)
        self.assertIn('hp_6_ALPHA_OPAQUE_RUBBER_Shape', objects)
        self.assertIn('mp_24_MIDLOD_Shape', objects)
        self.assertIn('lp_29_ALPHA_OPAQUE_LODShape', objects)
        with open(os.path.join(out_path, 'material.mtl')) as f:
            mtl = f.read()
        self.assertIn('map_Kd textures/skin.png', mtl)
        self.assertIn('map_Kd textures/wl00.png', mtl)
        # glass: black with vertex alpha 0x85
        self.assertIn('newmtl skin-00000085\n', mtl)
        with Image.open(os.path.join(out_path, 'textures/skin-00000085.png')) as png:
            self.assertEqual(png.getextrema()[3][1], 0x85)
        with Image.open(os.path.join(out_path, 'textures/skin.png')) as png:
            self.assertEqual(png.getextrema()[3], (255, 255))
        with open(os.path.join(out_path, 'skins.json')) as f:
            skins = json.load(f)
        self.assertEqual(
            [(x['name'], x['label']) for x in skins],
            [('skin00', 'red'), ('skin01', 'black'), ('skin02', 'silver'), ('skinhp', 'purple')],
        )
        for skin in skins:
            self.assertTrue(os.path.exists(os.path.join(out_path, skin['texture'])))
        with open(os.path.join(out_path, 'geometry_extra.json')) as f:
            dummies = {x['name']: x['position'] for x in json.load(f)['dummies']}
        self.assertNotIn('DAMAGE01', dummies)
        # front left wheel: left is -X, front is +Y
        x, y, z = dummies['WHEEL_FRONT_LEFT']
        self.assertLess(x, 0)
        self.assertGreater(y, 0)
        self.assertLess(dummies['LIGHT_TAIL_LEFT1'][1], 0)
