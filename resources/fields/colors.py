from io import BufferedReader, BytesIO

from buffer_utils import read_byte, read_int, read_short, write_int, write_short, write_3int, read_3int
from parsers.resources.utils import transform_bitness, extract_number
from resources.fields import ResourceField


# transforms 0565, 1555 etc. colors to regular 8888
def transform_color_bitness(color, alpha_bitness, red_bitness, green_bitness, blue_bitness):
    alpha = transform_bitness(extract_number(color, alpha_bitness, red_bitness + green_bitness + blue_bitness),
                              alpha_bitness) if alpha_bitness else 0xFF
    red = transform_bitness(extract_number(color, red_bitness, green_bitness + blue_bitness), red_bitness)
    green = transform_bitness(extract_number(color, green_bitness, blue_bitness), green_bitness)
    blue = transform_bitness(extract_number(color, blue_bitness), blue_bitness)
    return red << 24 | green << 16 | blue << 8 | alpha


class Color24BitDosField(ResourceField):
    block_description = 'EA games 24-bit dos color, 00rrrrrr_00gggggg_00bbbbbb'

    @property
    def size(self):
        return 3

    def _read_internal(self, buffer, size, parent_read_data: dict = None):
        return self._transform_value(read_byte(buffer), read_byte(buffer), read_byte(buffer))

    def _transform_value(self, *values):
        red = transform_bitness(values[0], 6)
        green = transform_bitness(values[1], 6)
        blue = transform_bitness(values[2], 6)
        return red << 24 | green << 16 | blue << 8 | 255

    def _read_multiple_internal(self, buffer: [BufferedReader, BytesIO], size: int, length: int,
                                parent_read_data: dict = None):
        bts = list(buffer.read(length * 3))
        return [self._transform_value(*x)
                for x in (bts[i:i + 3]
                          for i in range(0, length * 3, 3))]

    def _write_internal(self, buffer, value):
        red = (value & 0xff000000) >> 26
        green = (value & 0xff0000) >> 18
        blue = (value & 0xff00) >> 10
        write_3int(buffer, red << 16 | green << 8 | blue, byteorder='big')


class Color24BitBigEndianField(ResourceField):
    block_description = 'EA games 24-bit color (big-endian), rrrrrrrr_gggggggg_bbbbbbbb'

    @property
    def size(self):
        return 3

    def _read_internal(self, buffer, size, parent_read_data: dict = None):
        return read_3int(buffer, byteorder='big') << 8 | 0xFF

    def _write_internal(self, buffer, value):
        write_3int(buffer, value >> 8, byteorder='big')


class Color24BitLittleEndianField(ResourceField):
    block_description = 'EA games 24-bit color (little-endian), rrrrrrrr_gggggggg_bbbbbbbb'

    @property
    def size(self):
        return 3

    def _read_internal(self, buffer, size, parent_read_data: dict = None):
        return read_3int(buffer) << 8 | 0xFF

    def _write_internal(self, buffer, value):
        write_3int(buffer, value >> 8)


class Color32BitField(ResourceField):
    block_description = 'EA games 32-bit ARGB color, aaaaaaaa_rrrrrrrr_gggggggg_bbbbbbbb'

    @property
    def size(self):
        return 4

    def _read_internal(self, buffer, size, parent_read_data: dict = None):
        value = read_int(buffer)
        # ARGB => RGBA
        return (value & 0x00_ff_ff_ff) << 8 | (value & 0xff_00_00_00) >> 24

    def _write_internal(self, buffer, value):
        # RGBA => ARGB
        write_int(buffer, (value & 0xff_ff_ff_00) >> 8 | (value & 0xff) << 24)


class Color16Bit0565Field(ResourceField):
    block_description = 'EA games 16-bit 0565 color, rrrrrggg_gggbbbbb'

    @property
    def size(self):
        return 2

    def _read_internal(self, buffer, size, parent_read_data: dict = None):
        return transform_color_bitness(read_short(buffer), 0, 5, 6, 5)

    def _write_internal(self, buffer, value):
        red = (value & 0xff000000) >> 27
        green = (value & 0xff0000) >> 18
        blue = (value & 0xff00) >> 11
        write_short(buffer, red << 11 | green << 5 | blue)


class Color16Bit1555Field(ResourceField):
    block_description = 'EA games 16-bit 1555 color, arrrrrgg_gggbbbbb'

    @property
    def size(self):
        return 2

    def _read_internal(self, buffer: [BufferedReader, BytesIO], size: int, parent_read_data: dict = None):
        return transform_color_bitness(read_short(buffer), 1, 5, 5, 5)

    def _write_internal(self, buffer, value):
        red = (value & 0xff000000) >> 27
        green = (value & 0xff0000) >> 18
        blue = (value & 0xff00) >> 11
        write_short(buffer, red << 11 | green << 5 | blue)
