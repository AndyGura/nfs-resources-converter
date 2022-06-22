from buffer_utils import read_byte, read_int, read_short, write_int, write_short, write_3int
from parsers.resources.utils import transform_bitness, transform_color_bitness
from resources.fields import ResourceField


class Color24BitDosField(ResourceField):
    block_description = 'EA games 24-bit dos color, 00rrrrrr_00gggggg_00bbbbbb'

    @property
    def size(self):
        return 3

    def _read_internal(self, buffer, size):
        red = transform_bitness(read_byte(buffer), 6)
        green = transform_bitness(read_byte(buffer), 6)
        blue = transform_bitness(read_byte(buffer), 6)
        return red << 24 | green << 16 | blue << 8 | 255

    def _write_internal(self, buffer, value):
        red = (value & 0xff000000) >> 26
        green = (value & 0xff0000) >> 18
        blue = (value & 0xff00) >> 10
        write_3int(buffer, red << 16 | green << 8 | blue, byteorder='big')


class Color24BitField(ResourceField):
    block_description = 'EA games 24-bit color, rrrrrrrr_gggggggg_bbbbbbbb'

    @property
    def size(self):
        return 3

    def _read_internal(self, buffer, size):
        return read_byte(buffer) << 24 | read_byte(buffer) << 16 | read_byte(buffer) << 8 | 255

    def _write_internal(self, buffer, value):
        red = (value & 0xff000000) >> 24
        green = (value & 0xff0000) >> 16
        blue = (value & 0xff00) >> 8
        write_3int(buffer, red << 16 | green << 8 | blue, byteorder='big')


class Color32BitField(ResourceField):
    block_description = 'EA games 32-bit ARGB color, aaaaaaaa_rrrrrrrr_gggggggg_bbbbbbbb'

    @property
    def size(self):
        return 4

    def _read_internal(self, buffer, size):
        value = read_int(buffer)
        # ARGB => RGBA
        return (value & 0x00_ff_ff_ff) << 8 | (value & 0xff_00_00_00) >> 24

    def _write_internal(self, buffer, value):
        # RGBA => ARGB
        write_int(buffer, (value & 0xff_ff_ff_00) >> 8 | (value & 0xff) << 24)


class Color16BitField(ResourceField):
    block_description = 'EA games 16-bit 0565 color, rrrrrggg_gggbbbbb'

    @property
    def size(self):
        return 2

    def _read_internal(self, buffer, size):
        return transform_color_bitness(read_short(buffer), 0, 5, 6, 5)

    def _write_internal(self, buffer, value):
        red = (value & 0xff000000) >> 27
        green = (value & 0xff0000) >> 18
        blue = (value & 0xff00) >> 11
        write_short(buffer, red << 11 | green << 5 | blue)
