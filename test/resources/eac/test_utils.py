import unittest

from PIL import Image

from resources.eac.utils import quantize_images_to_8bit, build_8bit_palette


def _solid_image(width, height, rgba):
    return Image.frombytes('RGBA', (width, height), bytes(rgba) * (width * height))


class TestQuantizeImagesTo8Bit(unittest.TestCase):
    def test_single_image_indices_resolve_back_to_its_own_colors(self):
        image = Image.frombytes('RGBA', (2, 1), bytes([255, 0, 0, 255, 0, 255, 0, 255]))
        ([indices], palette) = quantize_images_to_8bit([image])
        self.assertEqual([palette[i] for i in indices], [0xFF0000FF, 0x00FF00FF])

    def test_multiple_images_share_one_palette(self):
        red = _solid_image(2, 2, (255, 0, 0, 255))
        blue = _solid_image(2, 2, (0, 0, 255, 255))
        (indices_per_image, palette) = quantize_images_to_8bit([red, blue])
        self.assertEqual(len(indices_per_image), 2)
        red_colors = {palette[i] for i in indices_per_image[0]}
        blue_colors = {palette[i] for i in indices_per_image[1]}
        self.assertEqual(red_colors, {0xFF0000FF})
        self.assertEqual(blue_colors, {0x0000FFFF})

    def test_fully_transparent_pixels_get_a_dedicated_zero_alpha_entry(self):
        image = Image.frombytes('RGBA', (2, 1), bytes([255, 0, 0, 255, 10, 20, 30, 0]))
        ([indices], palette) = quantize_images_to_8bit([image])
        self.assertEqual(palette[indices[1]] & 0xFF, 0)
        self.assertEqual(palette[indices[0]] & 0xFF, 255)

    def test_opaque_image_has_no_reserved_transparent_entry(self):
        image = _solid_image(2, 2, (255, 0, 0, 255))
        (_, palette) = quantize_images_to_8bit([image])
        self.assertTrue(all((c & 0xFF) == 255 for c in palette))


class TestBuild8BitPalette(unittest.TestCase):
    def test_defaults_to_32bit_format_unconverted(self):
        pal = build_8bit_palette([0xFF0000FF, 0x00FF00FF], '32Bit color format palette', id='test')
        self.assertEqual(pal['resource_id'], '32Bit color format palette')
        self.assertEqual(pal['colors']['data'], [0xFF0000FF, 0x00FF00FF])

    def test_converts_to_the_requested_format(self):
        pal = build_8bit_palette([0xFF0000FF, 0x00FF00FF], '16Bit_0565 color format palette', id='test')
        self.assertEqual(pal['resource_id'], '16Bit_0565 color format palette')
        self.assertEqual(len(pal['colors']['data']), 2)
