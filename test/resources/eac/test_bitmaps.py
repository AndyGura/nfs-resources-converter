import copy
import unittest

from resources.eac.bitmaps import EacImage, EacPalette, mipmap_level_dims


class TestBitmap(unittest.TestCase):
    block = EacImage()

    def _gen_single_pixel_bitmap(self, resource_id, pixels_data):
        return (bytes([resource_id])
                + b'\x00\x00\x00\x01\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                + bytes(pixels_data))

    def _gen_two_pixels_bitmap(self, resource_id, pixels_data):
        return (bytes([resource_id])
                + b'\x00\x00\x00\x02\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                + bytes(pixels_data))

    def _get_serialized_pixel_data(self, data):
        return self.block.pack(data)[16:]

    def test_bitmap_16bit_4444_should_be_translated_correctly(self):
        # 0x1234 -> A=1, R=2, G=3, B=4 -> 0x22334411
        b = self._gen_single_pixel_bitmap(0x6D, bytes([0x34, 0x12]))
        data = self.block.unpack_from_bytes(b)
        self.assertEqual(data['bitmap'][0], 0x22334411)

    def test_bitmap_16bit_4444_should_be_saved_correctly(self):
        b = self._gen_single_pixel_bitmap(0x6D, bytes([0, 0]))
        data = self.block.unpack_from_bytes(b)
        data['bitmap'][0] = 0x22334411
        serialized_pixel = self._get_serialized_pixel_data(data)
        self.assertListEqual(list(serialized_pixel), [0x34, 0x12])

    def test_bitmap_16bit_0565_should_be_translated_correctly(self):
        # 0x1234 -> 0b0001001000110100
        # red part: 00010 -> 0001_0000 -> 16
        # green part: 010001 -> 0100_0101 -> 69
        # blue part: 10100 -> 1010_0101 -> 165
        b = self._gen_single_pixel_bitmap(0x78, bytes([0x34, 0x12]))
        data = self.block.unpack_from_bytes(b)
        self.assertEqual(data['bitmap'][0], 0x1045A5FF)

    def test_bitmap_16bit_0565_should_be_saved_correctly(self):
        b = self._gen_single_pixel_bitmap(0x78, bytes([0, 0]))
        data = self.block.unpack_from_bytes(b)
        data['bitmap'][0] = 0x1045A5FF
        serialized_pixel = self._get_serialized_pixel_data(data)
        self.assertListEqual(list(serialized_pixel), [0x34, 0x12])

    def test_bitmap_16bit_0565_transparent_should_be_translated_correctly(self):
        # 0x07C0 is transparent
        b = self._gen_single_pixel_bitmap(0x78, bytes([0xC0, 0x07]))
        data = self.block.unpack_from_bytes(b)
        self.assertEqual(data['bitmap'][0], 0)

    def test_bitmap_16bit_0565_transparent_should_be_saved_correctly(self):
        b = self._gen_single_pixel_bitmap(0x78, bytes([0, 0]))
        data = self.block.unpack_from_bytes(b)
        data['bitmap'][0] = 0
        serialized_pixel = self._get_serialized_pixel_data(data)
        self.assertListEqual(list(serialized_pixel), [0xC0, 0x07])

    def test_bitmap_4bit_should_be_translated_correctly(self):
        b = self._gen_two_pixels_bitmap(0x7A, bytes([0x12]))
        data = self.block.unpack_from_bytes(b)
        self.assertEqual(data['bitmap'][0][0], 0xFFFFFF11)
        self.assertEqual(data['bitmap'][0][1], 0xFFFFFF22)

    def test_bitmap_4bit_swapped_should_be_translated_correctly(self):
        b = self._gen_two_pixels_bitmap(0x79, bytes([0x12]))
        data = self.block.unpack_from_bytes(b)
        self.assertEqual(data['bitmap'][0][0], 0xFFFFFF22)
        self.assertEqual(data['bitmap'][0][1], 0xFFFFFF11)

    def test_bitmap_8bit_should_be_translated_correctly(self):
        b = self._gen_single_pixel_bitmap(0x7B, bytes([0x42]))
        data = self.block.unpack_from_bytes(b)
        self.assertEqual(data['bitmap'][0], 0x42)

    def test_bitmap_16bit_1555_should_be_translated_correctly(self):
        # 0x9234 -> 0b1001001000110100
        # alpha part: 1 -> 1111_1111 -> 255
        # red part: 00100 -> 0010_0001 -> 33
        # green part: 10001 -> 1000_1100 -> 140
        # blue part: 10100 -> 1010_0101 -> 165
        b = self._gen_single_pixel_bitmap(0x7E, bytes([0x34, 0x92]))
        data = self.block.unpack_from_bytes(b)
        self.assertEqual(data['bitmap'][0], 0x218CA5FF)

    def test_bitmap_16bit_1555_should_be_saved_correctly(self):
        b = self._gen_single_pixel_bitmap(0x7E, bytes([0, 0]))
        data = self.block.unpack_from_bytes(b)
        data['bitmap'][0] = 0x218CA5FF
        serialized_pixel = self._get_serialized_pixel_data(data)
        self.assertListEqual(list(serialized_pixel), [0x34, 0x92])

    def test_bitmap_24bit_should_be_translated_correctly(self):
        b = self._gen_single_pixel_bitmap(0x7F, bytes([0x56, 0x34, 0x12]))
        data = self.block.unpack_from_bytes(b)
        self.assertEqual(data['bitmap'][0], 0x123456FF)

    def test_bitmap_24bit_should_be_saved_correctly(self):
        b = self._gen_single_pixel_bitmap(0x7F, bytes([0, 0, 0]))
        data = self.block.unpack_from_bytes(b)
        data['bitmap'][0] = 0x123456FF
        serialized_pixel = self._get_serialized_pixel_data(data)
        self.assertListEqual(list(serialized_pixel), [0x56, 0x34, 0x12])

    def test_bitmap_32bit_should_be_translated_correctly(self):
        # ARGB 0x12345678 -> RGBA 0x34567812
        b = self._gen_single_pixel_bitmap(0x7D, bytes([0x78, 0x56, 0x34, 0x12]))
        data = self.block.unpack_from_bytes(b)
        self.assertEqual(data['bitmap'][0], 0x34567812)

    def test_bitmap_32bit_should_be_saved_correctly(self):
        b = self._gen_single_pixel_bitmap(0x7D, bytes([0, 0, 0, 0]))
        data = self.block.unpack_from_bytes(b)
        data['bitmap'][0] = 0x34567812
        serialized_pixel = self._get_serialized_pixel_data(data)
        self.assertListEqual(list(serialized_pixel), [0x78, 0x56, 0x34, 0x12])

    # TODO add tests, similar to test_ffn_can_be_reconstructed_from_files to few file formats


class TestPalette(unittest.TestCase):
    block = EacPalette()

    def _gen_single_color_palette(self, resource_id, color_data):
        return (bytes([resource_id])
                + b'\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00'
                + bytes(color_data))

    def test_color_24bit_dos_should_be_translated_correctly(self):
        b = self._gen_single_color_palette(0x22, bytes([0b0010_1010, 0b0001_0100, 0b0011_1011]))
        data = self.block.unpack_from_bytes(b)
        self.assertEqual(data['colors']['data'][0], 0b10101000_01010000_11101100_11111111)

    def test_color_24bit_dos_should_be_saved_correctly(self):
        b = self._gen_single_color_palette(0x22, bytes([0, 0, 0]))
        data = self.block.unpack_from_bytes(b)
        data['colors']['data'][0] = 0b11101010_01010000_10101101_11111111
        serialized_color = self.block.pack(data)[16:]
        self.assertListEqual(list(serialized_color), [0b0011_1010, 0b0001_0100, 0b0010_1011])

    def test_color_24bit_should_be_translated_correctly(self):
        b = self._gen_single_color_palette(0x24, bytes([0x12, 0x34, 0x56]))
        data = self.block.unpack_from_bytes(b)
        self.assertEqual(data['colors']['data'][0], 0x123456FF)

    def test_color_24bit_should_be_saved_correctly(self):
        b = self._gen_single_color_palette(0x24, bytes([0, 0, 0]))
        data = self.block.unpack_from_bytes(b)
        data['colors']['data'][0] = 0x123456FF
        serialized_color = self.block.pack(data)[16:]
        self.assertListEqual(list(serialized_color), [0x12, 0x34, 0x56])

    def test_color_16bit_unk_should_be_translated_correctly(self):
        # 0xF800 -> R=31, G=0, B=0 -> 0xFF0000FF
        b = self._gen_single_color_palette(0x29, bytes([0x00, 0xF8]))
        data = self.block.unpack_from_bytes(b)
        self.assertEqual(data['colors']['data'][0], 0xFF0000FF)

    def test_color_16bit_unk_should_be_saved_correctly(self):
        b = self._gen_single_color_palette(0x29, bytes([0, 0]))
        data = self.block.unpack_from_bytes(b)
        data['colors']['data'][0] = 0xFF0000FF
        serialized_color = self.block.pack(data)[16:]
        self.assertListEqual(list(serialized_color), [0x00, 0xF8])

    def test_color_32bit_should_be_translated_correctly(self):
        # ARGB 0x12345678 -> RGBA 0x34567812
        b = self._gen_single_color_palette(0x2A, bytes([0x78, 0x56, 0x34, 0x12]))
        data = self.block.unpack_from_bytes(b)
        self.assertEqual(data['colors']['data'][0], 0x34567812)

    def test_color_32bit_should_be_saved_correctly(self):
        b = self._gen_single_color_palette(0x2A, bytes([0, 0, 0, 0]))
        data = self.block.unpack_from_bytes(b)
        data['colors']['data'][0] = 0x34567812
        serialized_color = self.block.pack(data)[16:]
        self.assertListEqual(list(serialized_color), [0x78, 0x56, 0x34, 0x12])

    def test_color_16bit_1555_should_be_translated_correctly(self):
        # 0xF800 -> R=31, G=0, B=0 -> 0xFF0000FF
        b = self._gen_single_color_palette(0x2D, bytes([0x34, 0x92]))
        data = self.block.unpack_from_bytes(b)
        self.assertEqual(data['colors']['data'][0], 0x218CA5FF)

    def test_color_16bit_1555_should_be_saved_correctly(self):
        b = self._gen_single_color_palette(0x2D, bytes([0, 0]))
        data = self.block.unpack_from_bytes(b)
        data['colors']['data'][0] = 0x218CA5FF
        serialized_color = self.block.pack(data)[16:]
        self.assertListEqual(list(serialized_color), [0x34, 0x92])


def _make_image(resource_id, width, height, bitmap):
    block = EacImage()
    data = block.new_data()
    data['resource_id'] = resource_id
    data['width'] = width
    data['height'] = height
    data['bitmap'] = bitmap
    return block, data


def _roundtrip(block, data):
    return EacImage().unpack_from_bytes(block.pack(copy.deepcopy(data)))


class TestMipmapLevelDims(unittest.TestCase):
    def test_yields_halving_dims_down_to_1x1(self):
        self.assertEqual(list(mipmap_level_dims(8, 4)), [(4, 2), (2, 1), (1, 1)])

    def test_non_power_of_two_still_halves_and_rounds_up(self):
        self.assertEqual(list(mipmap_level_dims(6, 3)), [(3, 1), (1, 1)])


class TestGenerateMipmaps(unittest.TestCase):
    def test_rejects_non_power_of_two_dimensions(self):
        block, data = _make_image('32Bit color format bitmap', 6, 4, [0] * 24)
        self.assertRaises(ValueError, block.action_generate_mipmaps, data)

    def test_rejects_1x1_image(self):
        block, data = _make_image('32Bit color format bitmap', 1, 1, [0])
        self.assertRaises(ValueError, block.action_generate_mipmaps, data)

    def test_32bit_mipmaps_have_one_pixel_per_level_and_roundtrip(self):
        bitmap = [((x * 16) << 24) | ((y * 16) << 16) | 0x64FF for y in range(4) for x in range(4)]
        block, data = _make_image('32Bit color format bitmap', 4, 4, bitmap)
        block.action_generate_mipmaps(data)
        self.assertEqual(len(data['mipmaps']), 2 * 2 + 1 * 1)
        self.assertEqual(_roundtrip(block, data)['mipmaps'], data['mipmaps'])

    def test_8bit_mipmaps_reuse_source_indices_and_roundtrip(self):
        bitmap = [(y * 4 + x) % 200 for y in range(4) for x in range(4)]
        block, data = _make_image('8Bit', 4, 4, bitmap)
        block.action_generate_mipmaps(data)
        self.assertTrue(all(idx in bitmap for idx in data['mipmaps']))
        self.assertEqual(_roundtrip(block, data)['mipmaps'], data['mipmaps'])

    def test_4bit_mipmaps_roundtrip(self):
        # regression test: 4Bit mipmap levels have to be (de)serialized per-level (each with its
        # own width), not as one w*h-shaped grid like the base bitmap - see
        # `_mipmaps_native_to_internal`/`_mipmaps_internal_to_native`.
        native = bytes([0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0])
        block = EacImage()
        bitmap = block._native_to_internal('4Bit', 8, 2, native)
        _, data = _make_image('4Bit', 8, 2, bitmap)
        block.action_generate_mipmaps(data)
        self.assertEqual(_roundtrip(block, data)['mipmaps'], data['mipmaps'])
        self.assertEqual(_roundtrip(block, data)['bitmap'], data['bitmap'])


class TestConvertTo8Bit(unittest.TestCase):
    def test_generate_embedded_palette_produces_working_palette_and_roundtrips(self):
        bitmap = [((x * 16) << 24) | ((y * 16) << 16) | 0x64FF for y in range(4) for x in range(4)]
        block, data = _make_image('32Bit color format bitmap', 4, 4, bitmap)
        block.action_convert_to_8bit(data, channel='generate embedded palette', id='test/data')

        self.assertEqual(data['resource_id'], '8Bit')
        palette_colors = data['embedded_palette']['colors']['data']
        self.assertEqual([palette_colors[i] for i in data['bitmap']], bitmap)

        reread = _roundtrip(block, data)
        self.assertEqual(reread['bitmap'], data['bitmap'])
        self.assertEqual(reread['embedded_palette']['colors']['data'], palette_colors)

    def test_generate_embedded_palette_respects_palette_type(self):
        bitmap = [((x * 16) << 24) | ((y * 16) << 16) | 0x64FF for y in range(4) for x in range(4)]
        block, data = _make_image('32Bit color format bitmap', 4, 4, bitmap)
        block.action_convert_to_8bit(data, channel='generate embedded palette',
                                     palette_type='16Bit_0565 color format palette', id='test/data')
        self.assertEqual(data['embedded_palette']['resource_id'], '16Bit_0565 color format palette')
        self.assertEqual(_roundtrip(block, data)['embedded_palette']['resource_id'],
                         '16Bit_0565 color format palette')

    def test_generate_embedded_palette_quantizes_mipmaps_against_the_same_palette(self):
        # regression test: mipmaps used to be left as raw RGBA ints after this conversion, which
        # get misread as (mostly near-transparent) palette indices - see action_convert_to_8bit.
        bitmap = [((x * 60) << 24) | ((y * 60) << 16) | 0x64FF for y in range(4) for x in range(4)]
        block, data = _make_image('32Bit color format bitmap', 4, 4, bitmap)
        block.action_generate_mipmaps(data)
        mipmap_count = len(data['mipmaps'])
        block.action_convert_to_8bit(data, channel='generate embedded palette', id='test/data')

        self.assertEqual(len(data['mipmaps']), mipmap_count)
        palette_colors = data['embedded_palette']['colors']['data']
        self.assertTrue(all(0 <= idx < len(palette_colors) for idx in data['mipmaps']))
        # every mip pixel should resolve to a real (opaque) palette color, not the all-zero
        # fallback an out-of-range/garbage index would previously have produced
        self.assertTrue(all((palette_colors[idx] & 0xFF) != 0 for idx in data['mipmaps']))

        reread = _roundtrip(block, data)
        self.assertEqual(reread['mipmaps'], data['mipmaps'])
        self.assertEqual(reread['bitmap'], data['bitmap'])

    def test_converting_away_from_8bit_clears_stale_palette_fields(self):
        bitmap = [(y * 4 + x) % 16 for y in range(4) for x in range(4)]
        block, data = _make_image('8Bit', 4, 4, bitmap)
        palette = EacPalette().new_data()
        palette['resource_id'] = '32Bit color format palette'
        palette['colors']['data'] = [0xFF0000FF] * 256
        data['embedded_palette'] = palette

        block.action_convert_to_4bit(data, mode='4Bit', channel='')
        self.assertIsNone(data['embedded_palette'])

        # a stray, unconverted embedded_palette would get written anyway (its write-time presence
        # check doesn't look at resource_id) and misalign every field read after it
        _, clean_data = _make_image('4Bit', 4, 4, data['bitmap'])
        self.assertEqual(len(block.pack(copy.deepcopy(data))), len(block.pack(clean_data)))

    def test_4bit_source_mipmaps_are_widened_and_roundtrip(self):
        native = bytes([0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0])
        block = EacImage()
        bitmap4 = block._native_to_internal('4Bit', 8, 2, native)
        _, data = _make_image('4Bit', 8, 2, bitmap4)
        block.action_generate_mipmaps(data)
        block.action_convert_to_8bit(data, channel='', id='test/data')
        self.assertTrue(all(isinstance(idx, int) for idx in data['mipmaps']))
        self.assertEqual(_roundtrip(block, data)['mipmaps'], data['mipmaps'])


class TestConvertTo4Bit(unittest.TestCase):
    def test_8bit_source_mipmaps_are_converted_and_roundtrip(self):
        block, data = _make_image('8Bit', 4, 4, [(y * 4 + x) % 16 for y in range(4) for x in range(4)])
        block.action_generate_mipmaps(data)
        block.action_convert_to_4bit(data, mode='4Bit', channel='')

        self.assertEqual(data['resource_id'], '4Bit')
        self.assertTrue(all(isinstance(row, list) for row in data['mipmaps']))
        # 4Bit only keeps 4 bits per value, so a value is only guaranteed stable once it has
        # already been through one write/read cycle
        once = _roundtrip(block, data)
        twice = _roundtrip(block, once)
        self.assertEqual(twice['bitmap'], once['bitmap'])
        self.assertEqual(twice['mipmaps'], once['mipmaps'])

    def test_rgba_source_mipmaps_are_converted(self):
        bitmap = [((x * 16) << 24) | ((y * 16) << 16) | 0x64FF for y in range(4) for x in range(4)]
        block, data = _make_image('32Bit color format bitmap', 4, 4, bitmap)
        block.action_generate_mipmaps(data)
        block.action_convert_to_4bit(data, mode='4Bit', channel='red')

        self.assertEqual(data['resource_id'], '4Bit')
        self.assertTrue(all(isinstance(row, list) for row in data['mipmaps']))
        # 4Bit is lossy (4 bits per channel value), so a value is only guaranteed stable once it
        # has already been through one write/read cycle
        once = _roundtrip(block, data)
        twice = _roundtrip(block, once)
        self.assertEqual(twice['bitmap'], once['bitmap'])
        self.assertEqual(twice['mipmaps'], once['mipmaps'])


class TestConvertToRgba(unittest.TestCase):
    def test_use_palette_converts_mipmaps_through_the_same_palette(self):
        # regression test: mipmaps used to stay as raw palette indices after this conversion,
        # which get misread as (mostly out-of-range, near-black) colors - see
        # action_convert_to_rgba.
        block, data = _make_image('8Bit', 4, 4, [(y * 4 + x) % 200 for y in range(4) for x in range(4)])
        palette = EacPalette().new_data()
        palette['resource_id'] = '32Bit color format palette'
        palette['colors']['data'] = [((i * 3) % 256) << 24 | ((i * 5) % 256) << 16 | ((i * 7) % 256) << 8 | 255
                                     for i in range(256)]
        data['embedded_palette'] = palette
        block.action_generate_mipmaps(data)
        mipmap_indices = list(data['mipmaps'])

        block.action_convert_to_rgba(data, color_mode='32Bit color format bitmap', output_colors='use palette',
                                     id='test/data')

        self.assertEqual(data['resource_id'], '32Bit color format bitmap')
        self.assertEqual(data['mipmaps'], [palette['colors']['data'][i] for i in mipmap_indices])
        self.assertIsNone(data['embedded_palette'])

        reread = _roundtrip(block, data)
        self.assertEqual(reread['bitmap'], data['bitmap'])
        self.assertEqual(reread['mipmaps'], data['mipmaps'])

    def test_converting_away_from_8bit_clears_stale_palette_fields(self):
        block, data = _make_image('8Bit', 2, 2, [0, 1, 2, 3])
        palette = EacPalette().new_data()
        palette['resource_id'] = '32Bit color format palette'
        palette['colors']['data'] = [0xFF0000FF] * 256
        data['embedded_palette'] = palette

        block.action_convert_to_rgba(data, color_mode='32Bit color format bitmap', output_colors='black-white',
                                     id='test/data')
        self.assertIsNone(data['embedded_palette'])
