import os
import re
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
    def test_car_meshes_get_texture_pages(self):
        from library import require_file
        from serializers import get_serializer

        name, block, data = require_file('test/samples/356b.crp')
        serializer = get_serializer(block, data)
        serializer.patch_settings(
            {'geometry__save_obj': True, 'geometry__save_blend': False, 'geometry__export_to_gg_web_engine': False}
        )
        with tempfile.TemporaryDirectory() as out:
            serializer.serialize(data, out, id=name, block=block)
            # wheel and window materials keep the alpha channel, other pages are opaque
            for page, size in [('0', 256), ('1', 256), ('2', 256), ('3', 128), ('3_alpha', 128), ('4_alpha', 64)]:
                with Image.open(os.path.join(out, 'textures', f'page_{page}.png')) as img:
                    self.assertEqual(img.size, (size, size))
            with open(os.path.join(out, 'material.mtl')) as f:
                self.assertEqual(
                    re.findall(r'newmtl (\S+)', f.read()),
                    ['page_0', 'page_1', 'page_2', 'page_3', 'page_3_alpha', 'page_4_alpha'],
                )
            with open(os.path.join(out, 'geometry.obj')) as f:
                obj = f.read()
            body_meshes = re.findall(r'\no (Body_LOD1_ai0[^\n]*)\n', obj)
            self.assertIn('Body_LOD1_ai0_page_0', body_meshes)
            self.assertIn('Body_LOD1_ai0_page_0_damaged', body_meshes)
            self.assertIn('usemtl page_0', obj)
