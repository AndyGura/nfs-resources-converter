import unittest

from io import BytesIO

from library.context import ReadContext
from resources.eac.bitmaps import EacImage, EacPalette




class TestBitmap(unittest.TestCase):
    block = EacImage()

    def _gen_single_pixel_bitmap(self, resource_id, pixels_data):
        return BytesIO(bytes([resource_id])
                       + b'\x00\x00\x00\x01\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                       + bytes(pixels_data))

    def _gen_two_pixels_bitmap(self, resource_id, pixels_data):
        return BytesIO(bytes([resource_id])
                       + b'\x00\x00\x00\x02\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                       + bytes(pixels_data))

    def _get_serialized_pixel_data(self, data):
        return self.block.pack(data)[16:]

    def test_bitmap_16bit_4444_should_be_translated_correctly(self):
        # 0x1234 -> A=1, R=2, G=3, B=4 -> 0x22334411
        buf = self._gen_single_pixel_bitmap(0x6D, bytes([0x34, 0x12]))
        data = self.block.unpack(ReadContext(buf))
        self.assertEqual(data['bitmap']['data'][0], 0x22334411)

    def test_bitmap_16bit_4444_should_be_saved_correctly(self):
        buf = self._gen_single_pixel_bitmap(0x6D, bytes([0, 0]))
        data = self.block.unpack(ReadContext(buf))
        data['bitmap']['data'][0] = 0x22334411
        serialized_pixel = self._get_serialized_pixel_data(data)
        self.assertListEqual(list(serialized_pixel), [0x34, 0x12])

    def test_bitmap_16bit_0565_should_be_translated_correctly(self):
        # 0x1234 -> 0b0001001000110100
        # red part: 00010 -> 0001_0000 -> 16
        # green part: 010001 -> 0100_0101 -> 69
        # blue part: 10100 -> 1010_0101 -> 165
        buf = self._gen_single_pixel_bitmap(0x78, bytes([0x34, 0x12]))
        data = self.block.unpack(ReadContext(buf))
        self.assertEqual(data['bitmap']['data'][0], 0x1045A5FF)

    def test_bitmap_16bit_0565_should_be_saved_correctly(self):
        buf = self._gen_single_pixel_bitmap(0x78, bytes([0, 0]))
        data = self.block.unpack(ReadContext(buf))
        data['bitmap']['data'][0] = 0x1045A5FF
        serialized_pixel = self._get_serialized_pixel_data(data)
        self.assertListEqual(list(serialized_pixel), [0x34, 0x12])

    def test_bitmap_16bit_0565_transparent_should_be_translated_correctly(self):
        # 0x07C0 is transparent
        buf = self._gen_single_pixel_bitmap(0x78, bytes([0xC0, 0x07]))
        data = self.block.unpack(ReadContext(buf))
        self.assertEqual(data['bitmap']['data'][0], 0)

    def test_bitmap_16bit_0565_transparent_should_be_saved_correctly(self):
        buf = self._gen_single_pixel_bitmap(0x78, bytes([0, 0]))
        data = self.block.unpack(ReadContext(buf))
        data['bitmap']['data'][0] = 0
        serialized_pixel = self._get_serialized_pixel_data(data)
        self.assertListEqual(list(serialized_pixel), [0xC0, 0x07])

    def test_bitmap_4bit_should_be_translated_correctly(self):
        buf = self._gen_two_pixels_bitmap(0x7A, bytes([0x12]))
        data = self.block.unpack(ReadContext(buf))
        self.assertEqual(data['bitmap']['data'][0][0], 0xFFFFFF11)
        self.assertEqual(data['bitmap']['data'][0][1], 0xFFFFFF22)

    def test_bitmap_4bit_swapped_should_be_translated_correctly(self):
        buf = self._gen_two_pixels_bitmap(0x79, bytes([0x12]))
        data = self.block.unpack(ReadContext(buf))
        self.assertEqual(data['bitmap']['data'][0][0], 0xFFFFFF22)
        self.assertEqual(data['bitmap']['data'][0][1], 0xFFFFFF11)

    def test_bitmap_8bit_should_be_translated_correctly(self):
        buf = self._gen_single_pixel_bitmap(0x7B, bytes([0x42]))
        data = self.block.unpack(ReadContext(buf))
        self.assertEqual(data['bitmap']['data'][0], 0x42)

    def test_bitmap_16bit_1555_should_be_translated_correctly(self):
        # 0x9234 -> 0b1001001000110100
        # alpha part: 1 -> 1111_1111 -> 255
        # red part: 00100 -> 0010_0001 -> 33
        # green part: 10001 -> 1000_1100 -> 140
        # blue part: 10100 -> 1010_0101 -> 165
        buf = self._gen_single_pixel_bitmap(0x7E, bytes([0x34, 0x92]))
        data = self.block.unpack(ReadContext(buf))
        self.assertEqual(data['bitmap']['data'][0], 0x218CA5FF)

    def test_bitmap_16bit_1555_should_be_saved_correctly(self):
        buf = self._gen_single_pixel_bitmap(0x7E, bytes([0, 0]))
        data = self.block.unpack(ReadContext(buf))
        data['bitmap']['data'][0] = 0x218CA5FF
        serialized_pixel = self._get_serialized_pixel_data(data)
        self.assertListEqual(list(serialized_pixel), [0x34, 0x92])

    def test_bitmap_24bit_should_be_translated_correctly(self):
        buf = self._gen_single_pixel_bitmap(0x7F, bytes([0x56, 0x34, 0x12]))
        data = self.block.unpack(ReadContext(buf))
        self.assertEqual(data['bitmap']['data'][0], 0x123456FF)

    def test_bitmap_24bit_should_be_saved_correctly(self):
        buf = self._gen_single_pixel_bitmap(0x7F, bytes([0, 0, 0]))
        data = self.block.unpack(ReadContext(buf))
        data['bitmap']['data'][0] = 0x123456FF
        serialized_pixel = self._get_serialized_pixel_data(data)
        self.assertListEqual(list(serialized_pixel), [0x56, 0x34, 0x12])

    def test_bitmap_32bit_should_be_translated_correctly(self):
        # ARGB 0x12345678 -> RGBA 0x34567812
        buf = self._gen_single_pixel_bitmap(0x7D, bytes([0x78, 0x56, 0x34, 0x12]))
        data = self.block.unpack(ReadContext(buf))
        self.assertEqual(data['bitmap']['data'][0], 0x34567812)

    def test_bitmap_32bit_should_be_saved_correctly(self):
        buf = self._gen_single_pixel_bitmap(0x7D, bytes([0, 0, 0, 0]))
        data = self.block.unpack(ReadContext(buf))
        data['bitmap']['data'][0] = 0x34567812
        serialized_pixel = self._get_serialized_pixel_data(data)
        self.assertListEqual(list(serialized_pixel), [0x78, 0x56, 0x34, 0x12])



class TestPalette(unittest.TestCase):
    block = EacPalette()

    def _gen_single_color_palette(self, resource_id, color_data):
        return BytesIO(bytes([resource_id])
                       + b'\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00'
                       + bytes(color_data))

    def test_color_24bit_dos_should_be_translated_correctly(self):
        buf = self._gen_single_color_palette(0x22, bytes([0b0010_1010, 0b0001_0100, 0b0011_1011]))
        data = self.block.unpack(ReadContext(buf))
        self.assertEqual(data['colors']['data'][0], 0b10101000_01010000_11101100_11111111)

    def test_color_24bit_dos_should_be_saved_correctly(self):
        buf = self._gen_single_color_palette(0x22, bytes([0, 0, 0]))
        data = self.block.unpack(ReadContext(buf))
        data['colors']['data'][0] = 0b11101010_01010000_10101101_11111111
        serialized_color = self.block.pack(data)[16:]
        self.assertListEqual(list(serialized_color), [0b0011_1010, 0b0001_0100, 0b0010_1011])

    def test_color_24bit_should_be_translated_correctly(self):
        buf = self._gen_single_color_palette(0x24, bytes([0x12, 0x34, 0x56]))
        data = self.block.unpack(ReadContext(buf))
        self.assertEqual(data['colors']['data'][0], 0x123456FF)

    def test_color_24bit_should_be_saved_correctly(self):
        buf = self._gen_single_color_palette(0x24, bytes([0, 0, 0]))
        data = self.block.unpack(ReadContext(buf))
        data['colors']['data'][0] = 0x123456FF
        serialized_color = self.block.pack(data)[16:]
        self.assertListEqual(list(serialized_color), [0x12, 0x34, 0x56])

    def test_color_16bit_unk_should_be_translated_correctly(self):
        # 0xF800 -> R=31, G=0, B=0 -> 0xFF0000FF
        buf = self._gen_single_color_palette(0x29, bytes([0x00, 0xF8]))
        data = self.block.unpack(ReadContext(buf))
        self.assertEqual(data['colors']['data'][0], 0xFF0000FF)

    def test_color_16bit_unk_should_be_saved_correctly(self):
        buf = self._gen_single_color_palette(0x29, bytes([0, 0]))
        data = self.block.unpack(ReadContext(buf))
        data['colors']['data'][0] = 0xFF0000FF
        serialized_color = self.block.pack(data)[16:]
        self.assertListEqual(list(serialized_color), [0x00, 0xF8])

    def test_color_32bit_should_be_translated_correctly(self):
        # ARGB 0x12345678 -> RGBA 0x34567812
        buf = self._gen_single_color_palette(0x2A, bytes([0x78, 0x56, 0x34, 0x12]))
        data = self.block.unpack(ReadContext(buf))
        self.assertEqual(data['colors']['data'][0], 0x34567812)

    def test_color_32bit_should_be_saved_correctly(self):
        buf = self._gen_single_color_palette(0x2A, bytes([0, 0, 0, 0]))
        data = self.block.unpack(ReadContext(buf))
        data['colors']['data'][0] = 0x34567812
        serialized_color = self.block.pack(data)[16:]
        self.assertListEqual(list(serialized_color), [0x78, 0x56, 0x34, 0x12])

    def test_color_16bit_0565_should_be_translated_correctly(self):
        # 0xF800 -> R=31, G=0, B=0 -> 0xFF0000FF
        buf = self._gen_single_color_palette(0x2D, bytes([0x00, 0xF8]))
        data = self.block.unpack(ReadContext(buf))
        self.assertEqual(data['colors']['data'][0], 0xFF0000FF)

    def test_color_16bit_0565_should_be_saved_correctly(self):
        buf = self._gen_single_color_palette(0x2D, bytes([0, 0]))
        data = self.block.unpack(ReadContext(buf))
        data['colors']['data'][0] = 0xFF0000FF
        serialized_color = self.block.pack(data)[16:]
        self.assertListEqual(list(serialized_color), [0x00, 0xF8])
