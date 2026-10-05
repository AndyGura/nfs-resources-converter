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


class TestFce3GeometrySerializer(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    def _serialize_car_viv(self):
        from io import BytesIO

        from library import require_resource
        from library.loader import clear_file_cache
        from resources.eac.archives import BigfBlock
        from serializers import get_serializer
        from test.resources.eac.test_geometries import build_fce3_data

        fce_block, fce_data = build_fce3_data()
        tga = BytesIO()
        Image.new('RGBA', (4, 4), (255, 0, 0, 0)).save(tga, format='TGA')
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
            for alias, item_bytes in [('car.fce', fce_block.pack(fce_data)), ('car00.tga', tga.getvalue())]
        ]
        viv_path = os.path.join(self.tmp_dir, 'car.viv')
        with open(viv_path, 'wb') as f:
            f.write(bigf.pack(bigf_data))
        clear_file_cache(viv_path)
        fce_id = viv_path + '__children/0/item/data'
        (fce_id, block, data), _ = require_resource(fce_id)
        self.assertEqual(block.__class__.__name__, 'Fce3Geometry')
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
        # vertices are shared by triangle corners with the same UV: quad has 5 of them (vertex 2 has different UV in
        # both triangles). Double-sided triangle has 3 vertices and 2 faces
        self.assertEqual(len(re.findall(r'^v ', obj, re.MULTILINE)), 8)
        self.assertEqual(len(re.findall(r'^f ', obj, re.MULTILINE)), 4)
        # part position is applied, axes: (x, z, y)
        self.assertIn('v 1.0 4.0 2.0', obj)
        # V is stored from top to bottom, OBJ is from bottom to top
        self.assertIn('vt 0.0 0.75', obj)

    def test_exports_dummies(self):
        out_path = self._serialize_car_viv()
        import json

        with open(os.path.join(out_path, 'geometry_extra.json')) as f:
            extra = json.load(f)
        self.assertEqual(extra['dummies'], [{'name': 'HFLO', 'position': [0.5, 2.0, 0.25]}])
