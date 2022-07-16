import unittest
from io import BytesIO

from library.utils import read_byte
from resources.fields import (Color24BitDosField,
                              Color24BitLittleEndianField,
                              Color24BitBigEndianField,
                              Color32BitField,
                              Color16Bit0565Field,
                              )


class Color24BitDosFieldTest(unittest.TestCase):

    def test_should_read_3_bytes(self):
        ba = bytearray(b'')
        ba.append(0x10)
        ba.append(0x9A)
        ba.append(0x74)
        ba.append(0xCC)
        ba.append(0xCC)
        buffer = BytesIO(ba)
        result = Color24BitDosField().read(buffer, 5)
        self.assertEqual(buffer.tell(), 3)

    def test_should_read_from_current_position(self):
        ba = bytearray(b'')
        ba.append(255)
        ba.append(255)
        ba.append(255)
        ba.append(0)
        ba.append(0)
        ba.append(0)
        buffer = BytesIO(ba)
        buffer.seek(3)
        result = Color24BitDosField().read(buffer, 6)
        self.assertEqual(result, 255)

    def test_should_transform_correctly(self):
        ba = bytearray(b'')
        ba.append(255)
        ba.append(255)
        ba.append(255)
        buffer = BytesIO(ba)
        result = Color24BitDosField().read(buffer, 3)
        self.assertEqual(result, 0xffffffff)

    def test_transformation_2(self):
        ba = bytearray(b'')
        ba.append(127)
        ba.append(127)
        ba.append(127)
        buffer = BytesIO(ba)
        result = Color24BitDosField().read(buffer, 3)
        self.assertEqual(result, 0xffffffff)

    def test_transformation_3(self):
        ba = bytearray(b'')
        ba.append(63)
        ba.append(63)
        ba.append(63)
        buffer = BytesIO(ba)
        result = Color24BitDosField().read(buffer, 3)
        self.assertEqual(result, 0xffffffff)

    def test_transformation_control_value(self):
        ba = bytearray(b'')
        ba.append(31)
        ba.append(31)
        ba.append(31)
        buffer = BytesIO(ba)
        result = Color24BitDosField().read(buffer, 3)
        self.assertEqual(result, 0x7d7d7dff)

    def test_should_write_the_same_as_read(self):
        ba = bytearray(b'')
        ba.append(0x10)
        ba.append(0x1A)
        ba.append(0x4)
        buffer = BytesIO(ba)
        result = Color24BitDosField().read(buffer, 3)
        out_buffer = BytesIO()
        Color24BitDosField().write(out_buffer, result)
        buffer.seek(0)
        out_buffer.seek(0)
        self.assertEqual(buffer.read(), out_buffer.read())


class Color24BitLittleEndianFieldTest(unittest.TestCase):

    def test_should_read_3_bytes(self):
        ba = bytearray(b'')
        ba.append(0x10)
        ba.append(0x9A)
        ba.append(0x74)
        ba.append(0xCC)
        ba.append(0xCC)
        buffer = BytesIO(ba)
        result = Color24BitLittleEndianField().read(buffer, 3)
        self.assertEqual(buffer.tell(), 3)

    def test_should_read_correctly(self):
        ba = bytearray(b'')
        ba.append(0xFA)
        ba.append(0x03)
        ba.append(0x31)
        buffer = BytesIO(ba)
        result = Color24BitLittleEndianField().read(buffer, 3)
        self.assertEqual(result, 0x3103faff)

    def test_should_write_the_same_as_read(self):
        ba = bytearray(b'')
        ba.append(0x10)
        ba.append(0x1A)
        ba.append(0x4)
        buffer = BytesIO(ba)
        result = Color24BitLittleEndianField().read(buffer, 3)
        out_buffer = BytesIO()
        Color24BitLittleEndianField().write(out_buffer, result)
        buffer.seek(0)
        out_buffer.seek(0)
        self.assertEqual(buffer.read(), out_buffer.read())


class Color24BitBigEndianFieldTest(unittest.TestCase):

    def test_should_read_3_bytes(self):
        ba = bytearray(b'')
        ba.append(0x10)
        ba.append(0x9A)
        ba.append(0x74)
        ba.append(0xCC)
        ba.append(0xCC)
        buffer = BytesIO(ba)
        result = Color24BitBigEndianField().read(buffer, 3)
        self.assertEqual(buffer.tell(), 3)

    def test_should_read_correctly(self):
        ba = bytearray(b'')
        ba.append(0xFA)
        ba.append(0x03)
        ba.append(0x31)
        buffer = BytesIO(ba)
        result = Color24BitBigEndianField().read(buffer, 3)
        self.assertEqual(result, 0xfa0331ff)

    def test_should_write_the_same_as_read(self):
        ba = bytearray(b'')
        ba.append(0x10)
        ba.append(0x1A)
        ba.append(0x4)
        buffer = BytesIO(ba)
        result = Color24BitBigEndianField().read(buffer, 3)
        out_buffer = BytesIO()
        Color24BitBigEndianField().write(out_buffer, result)
        buffer.seek(0)
        out_buffer.seek(0)
        self.assertEqual(buffer.read(), out_buffer.read())


class Color32BitFieldTest(unittest.TestCase):

    def test_should_read_4_bytes(self):
        ba = bytearray(b'')
        ba.append(0x10)
        ba.append(0x9A)
        ba.append(0x74)
        ba.append(0xCC)
        ba.append(0xCC)
        buffer = BytesIO(ba)
        result = Color32BitField().read(buffer, 5)
        self.assertEqual(buffer.tell(), 4)

    def test_should_read_correctly(self):
        ba = bytearray(b'')
        ba.append(0x10)
        ba.append(0x9A)
        ba.append(0x74)
        ba.append(0xCC)
        buffer = BytesIO(ba)
        result = Color32BitField().read(buffer, 4)
        self.assertEqual(result, 0x749A10CC)

    def test_should_write_correct_value(self):
        buffer = BytesIO()
        Color32BitField().write(buffer, 0x749A10CC)
        self.assertEqual(buffer.tell(), 4)
        buffer.seek(0)
        values = [read_byte(buffer) for _ in range(4)]
        self.assertListEqual(values, [0x10, 0x9A, 0x74, 0xCC])

    def test_should_write_the_same_as_read(self):
        ba = bytearray(b'')
        ba.append(0x10)
        ba.append(0x9A)
        ba.append(0x74)
        ba.append(0xCC)
        buffer = BytesIO(ba)
        result = Color32BitField().read(buffer, 4)
        out_buffer = BytesIO()
        Color32BitField().write(out_buffer, result)
        buffer.seek(0)
        out_buffer.seek(0)
        self.assertEqual(buffer.read(), out_buffer.read())


class Color16Bit0565FieldTest(unittest.TestCase):

    def test_should_read_2_bytes(self):
        ba = bytearray(b'')
        ba.append(0x10)
        ba.append(0x9A)
        ba.append(0x74)
        ba.append(0xCC)
        ba.append(0xCC)
        buffer = BytesIO(ba)
        result = Color16Bit0565Field().read(buffer, 5)
        self.assertEqual(buffer.tell(), 2)

    def test_should_read_correctly(self):
        ba = bytearray(b'')
        ba.append(0b1001_1010)
        ba.append(0b1110_0000)
        buffer = BytesIO(ba)
        result = Color16Bit0565Field().read(buffer, 2)
        self.assertEqual(result, 0b1110_0110_0001_0000_1101_0110_1111_1111)

    def test_should_write_the_same_as_read(self):
        ba = bytearray(b'')
        ba.append(0x1F)
        ba.append(0x1A)
        buffer = BytesIO(ba)
        result = Color16Bit0565Field().read(buffer, 2)
        out_buffer = BytesIO()
        Color16Bit0565Field().write(out_buffer, result)
        buffer.seek(0)
        out_buffer.seek(0)
        self.assertEqual(buffer.read(), out_buffer.read())
