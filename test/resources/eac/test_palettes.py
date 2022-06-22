import unittest
from io import BytesIO

from resources.eac.palettes import Palette32BitResource


class Palette32BitResourceTest(unittest.TestCase):

    def test_should_read_a_regular_palette(self):
        ba = bytearray(b'')
        ba.append(0x2A)
        for i in range(15):
            ba.append(3)
        for i in range(256):
            ba.append(i)
            ba.append(i)
            ba.append(i)
            ba.append(i)
        buffer = BytesIO(ba)
        res = Palette32BitResource()
        res.read(buffer, 1040)
        self.assertEqual(res.resource_id, 0x2A)
        self.assertListEqual(res.unknowns, [3 for _ in range(15)])
        self.assertListEqual(res.colors, [(i << 24 | i << 16 | i << 8 | i) for i in range(256)])
