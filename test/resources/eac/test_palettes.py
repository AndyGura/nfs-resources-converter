import unittest
from io import BytesIO
from random import random

from resources.eac.palettes import Palette32Bit


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
        res = Palette32Bit()
        res.read(buffer, 1040)
        self.assertEqual(res.resource_id, 0x2A)
        self.assertListEqual(res.unknowns, [3 for _ in range(15)])
        self.assertListEqual(res.colors, [(i << 24 | i << 16 | i << 8 | i) for i in range(256)])

    def test_should_be_able_to_serialize_back(self):
        ba = bytearray(b'')
        ba.append(0x2A)
        for i in range(15 + 4 * 256):
            ba.append(round(random()*255))
        buffer = BytesIO(ba)
        res = Palette32Bit()
        res.read(buffer, len(ba))
        out_buffer = BytesIO()
        res.write(out_buffer)
        self.assertEqual(out_buffer.tell(), 16 + 4 * 256)
        out_buffer.seek(0)
        out_ba = out_buffer.read()
        self.assertEqual(ba, out_ba)

    def test_should_be_able_to_serialize_back_partial_palette(self):
        ba = bytearray(b'')
        ba.append(0x2A)
        for i in range(15 + 4 * 253):
            ba.append(round(random()*255))
        buffer = BytesIO(ba)
        res = Palette32Bit()
        res.read(buffer, len(ba))
        out_buffer = BytesIO()
        res.write(out_buffer)
        self.assertEqual(out_buffer.tell(), 16 + 4 * 253)
        out_buffer.seek(0)
        out_ba = out_buffer.read()
        self.assertEqual(ba, out_ba)


class Palette24BitDosResourceTest(unittest.TestCase):

    def test_should_be_able_to_serialize_back(self):
        ba = bytearray(b'')
        ba.append(0x2A)
        for i in range(15 + 3 * 256):
            ba.append(round(random()*63))
        buffer = BytesIO(ba)
        res = Palette32Bit()
        res.read(buffer, len(ba))
        out_buffer = BytesIO()
        res.write(out_buffer)
        self.assertEqual(out_buffer.tell(), 16 + 3 * 256)
        out_buffer.seek(0)
        out_ba = out_buffer.read()
        self.assertEqual(ba, out_ba)

