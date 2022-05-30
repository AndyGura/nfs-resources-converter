from abc import ABC, abstractmethod
from io import BufferedReader, SEEK_CUR

from buffer_utils import read_short, read_byte, read_int
from parsers.resources.base import BaseResource
from parsers.resources.utils import transform_bitness, transform_color_bitness


class BasePalette(BaseResource, ABC):
    color_size = 1
    rgb_colors = []

    def read(self, buffer: BufferedReader, length: int, path: str = None) -> int:
        buffer.seek(16, SEEK_CUR)
        self.rgb_colors = []
        for x in range(0, 256):
            color = self._read_color_from_palette_file(buffer)
            if x == 0xFF and self.is_last_color_transparent(color):
                self.rgb_colors.append(0)
                continue
            else:
                self.rgb_colors.append(color)
        return 16 + self.color_size * 256

    @abstractmethod
    def _read_color_from_palette_file(self, buffer: BufferedReader):
        pass

    def is_last_color_transparent(self, color):
        return color in [
            # green-ish
            0x00_EA_1C_FF,  # TNFS lost vegas map props
            0x00_EB_1C_FF,  # TNFS lost vegas map props
            0x00_FF_00_FF,
            0x04_FF_00_FF,
            0x0C_FF_00_FF,
            # 0x24_ff_10_FF,  # TNFS TRAFFC.CFM TODO not working??????
            0x28_FF_28_FF,
            0x28_FF_2C_FF,
            # blue
            0x00_00_FF_FF,
            0x00_00_FC_FF,  # TNFS Porsche 911 CFM
            # light blue
            0x00_FF_FF_FF,
            0x1a_ff_ff_ff,  # NFS2SE TRACKS/PC/TR000M.QFS
            0x48_ff_ff_FF,  # NFS2SE TRACKS/PC/TR020M.QFS
            # purple
            0xCE_1C_C6_FF,  # some TNFS map props
            0xF2_00_FF_FF,
            0xFF_00_F7_FF,  # TNFS AL2 map props
            0xFF_00_FF_FF,
            0xFF_00_F6_FF,  # TNFS NTRACKFM/AL3_T01.FAM map props
            # gray
            0x28_28_28_FF,  # car wheels
            0xFF_FF_FF_FF,  # map props
            0x00_00_00_FF,  # some menu items: SHOW/DIABLO.QFS
        ]

    def get_color(self, index: int) -> int:
        try:
            return self.rgb_colors[index]
        except IndexError:
            return 0

    def save_converted(self, path: str):
        with open(f'{path}.pal.txt', 'w') as f:
            f.write(f'{self.__class__.__name__}\n')
            f.write('Palette used in bitmap serialization. Contains mapping bitmap data bytes to RGBA colors.\n')
            for i, color in enumerate(self.rgb_colors):
                f.write(f'\n{hex(i)}:\t#{hex(color)}')


class Palette16Bit(BasePalette):
    color_size = 2

    def _read_color_from_palette_file(self, buffer: BufferedReader) -> int:
        color = read_short(buffer)
        return transform_color_bitness(color, 0, 5, 6, 5)


class Palette24Bit(BasePalette):
    color_size = 3

    def _read_color_from_palette_file(self, buffer: BufferedReader) -> int:
        return read_byte(buffer) << 24 | read_byte(buffer) << 16 | read_byte(buffer) << 8 | 255


class Palette24BitDos(BasePalette):
    color_size = 3

    def _read_color_from_palette_file(self, buffer: BufferedReader) -> int:
        red = transform_bitness(read_byte(buffer), 6)
        green = transform_bitness(read_byte(buffer), 6)
        blue = transform_bitness(read_byte(buffer), 6)
        return red << 24 | green << 16 | blue << 8 | 255


class Palette32Bit(BasePalette):
    color_size = 4

    def _read_color_from_palette_file(self, buffer: BufferedReader) -> int:
        value = read_int(buffer)
        # ARGB => RGBA
        return (value & 0x00_ff_ff_ff) << 8 | (value & 0xff_00_00_00) >> 24

    def is_last_color_transparent(self, color):
        # transparency already defined in color itself
        return False
