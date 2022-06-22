from abc import ABC, abstractmethod
from io import BufferedReader

from buffer_utils import read_short, read_byte, read_int
from parsers.resources.base import BaseResource
from parsers.resources.utils import transform_bitness, transform_color_bitness
from resources.eac.palettes import (Palette24BitResource, Palette16BitResource, Palette32BitResource,
                                    Palette24BitDosResource)


class BasePalette(BaseResource, ABC):
    color_size = 1
    rgb_colors = []
    new_res = Palette24BitResource

    def read(self, buffer: BufferedReader, length: int, path: str = None) -> int:
        start = buffer.tell()
        resource = self.new_res()
        resource.read(buffer, length)
        self.rgb_colors = resource.colors
        bytes_consumed = buffer.tell() - start
        if bytes_consumed < length:
            self.unknowns.append({'trailing_bytes': [read_byte(buffer) for _ in range(length - bytes_consumed)]})
        return length

    @abstractmethod
    def _read_color_from_palette_file(self, buffer: BufferedReader):
        pass

    def get_color(self, index: int) -> int:
        try:
            return self.rgb_colors[index]
        except IndexError:
            return 0

    def save_converted(self, path: str):
        super().save_converted(path)
        with open(f'{path}.pal.txt', 'w') as f:
            f.write(f'{self.__class__.__name__}\n')
            f.write('Palette used in bitmap serialization. Contains mapping bitmap data bytes to RGBA colors.\n')
            for i, color in enumerate(self.rgb_colors):
                f.write(f'\n{hex(i)}:\t#{hex(color)}')


class Palette16Bit(BasePalette):
    color_size = 2
    new_res = Palette16BitResource

    def _read_color_from_palette_file(self, buffer: BufferedReader) -> int:
        color = read_short(buffer)
        return transform_color_bitness(color, 0, 5, 6, 5)


class Palette24Bit(BasePalette):
    color_size = 3
    new_res = Palette24BitResource

    def _read_color_from_palette_file(self, buffer: BufferedReader) -> int:
        return read_byte(buffer) << 24 | read_byte(buffer) << 16 | read_byte(buffer) << 8 | 255


class Palette24BitDos(BasePalette):
    color_size = 3
    new_res = Palette24BitDosResource

    def _read_color_from_palette_file(self, buffer: BufferedReader) -> int:
        red = transform_bitness(read_byte(buffer), 6)
        green = transform_bitness(read_byte(buffer), 6)
        blue = transform_bitness(read_byte(buffer), 6)
        return red << 24 | green << 16 | blue << 8 | 255


class Palette32Bit(BasePalette):
    color_size = 4
    new_res = Palette32BitResource

    def _read_color_from_palette_file(self, buffer: BufferedReader) -> int:
        value = read_int(buffer)
        # ARGB => RGBA
        return (value & 0x00_ff_ff_ff) << 8 | (value & 0xff_00_00_00) >> 24
