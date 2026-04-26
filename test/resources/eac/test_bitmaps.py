import unittest

from six import BytesIO

from library.context import ReadContext
from resources.eac.bitmaps import EacPalette


class TestBitmap(unittest.TestCase):
    pass


class TestPalette(unittest.TestCase):
    block = EacPalette()

    def _get_single_color_palette_data(self, resorce_id, color_data):
        return BytesIO(bytes([resorce_id])
                       + b'\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00'
                       + bytes(color_data))

    def test_color_24bit_dos_should_be_translated_correctly(self):
        buf = self._get_single_color_palette_data(0x22, bytes([0b0010_1010, 0b0001_0100, 0b0011_1011]))
        data = self.block.unpack(ReadContext(buf))
        self.assertEqual(data['resource_id'], '24BitDos color format palette')
        self.assertEqual(data['num_colors'], 1)
        self.assertEqual(data['colors']['data'][0], 0b10101000_01010000_11101100_11111111)

    def test_color_24bit_dos_should_be_saved_correctly(self):
        buf = self._get_single_color_palette_data(0x22, bytes([0, 0, 0]))
        data = self.block.unpack(ReadContext(buf))
        data['colors']['data'][0] = 0b11101010_01010000_10101101_11111111
        serialized_color = self.block.pack(data)[16:]
        self.assertListEqual(list(serialized_color), [0b0011_1010, 0b0001_0100, 0b0010_1011])
