import math
from abc import ABC, abstractmethod
from functools import cached_property
from io import BufferedReader, SEEK_CUR
from typing import List

from PIL import Image

import settings
from buffer_utils import read_short, read_3int, read_byte
from parsers.resources.base import BaseResource
from parsers.resources.collections import ResourceDirectory, ArchiveResource
from parsers.resources.read_block_wrapper import ReadBlockWrapper
from parsers.resources.utils import transform_color_bitness
from resources.eac.palettes import BasePalette


class BaseBitmap(BaseResource, ABC):
    pixel_size = 1
    bitmap_bytes = None

    def _handle_trailing_bytes(self, buffer, trailing_bytes_length):
        raise f'Trailing bytes reader not implemented for {self.__class__.__name__}'

    def _get_directory_identifier(self):
        from parsers.resources.archives import SHPIArchive
        entity = self
        while entity and not isinstance(entity, SHPIArchive):
            entity = entity.parent
        return entity and entity.directory_identifier

    def read(self, buffer: BufferedReader, length: int, path: str = None) -> int:
        start_buffer_cur = buffer.tell()
        buffer.seek(1, SEEK_CUR)  # bitmap type byte
        block_size = read_3int(buffer)
        self.width = read_short(buffer)
        self.height = read_short(buffer)
        # TODO in WRAP directory there is no block size. What's there instead?
        directory_identifier = self._get_directory_identifier()
        if directory_identifier == 'WRAP':
            wrap_block_size = block_size
            block_size = 4 * int(math.ceil(self.pixel_size * self.width * self.height / 4)) + 16
            self.unknowns.append({'WRAP block_size': { 'value': wrap_block_size, 'real_block_size': block_size}})
        elif block_size == 0:
            # some NFS2 resources have block size equal to 0
            block_size = 4 * int(math.ceil(self.pixel_size * self.width * self.height / 4)) + 16
        trailing_bytes_length = length - block_size
        if trailing_bytes_length < 0:
            raise Exception(
                f'Too small bitmap block size {block_size}. Expected {self.pixel_size * self.width * self.height + 16}')
        if self.width > 8192 or self.height > 8192:
            raise Exception(f'Suspiciously large bitmap {self.width}/{self.height}')
        self.unknowns += [read_byte(buffer) for _ in range(4)]
        self.x = read_short(buffer)
        self.y = read_short(buffer)
        self.bitmap_bytes = buffer.read(block_size - 16)
        buffer.seek(start_buffer_cur + block_size)
        if trailing_bytes_length > 0:
            try:
                self._handle_trailing_bytes(buffer, trailing_bytes_length)
            except Exception as ex:
                buffer.seek(start_buffer_cur + length - trailing_bytes_length)
                self.unknowns.append({'Unhandled trailing bytes': { 'err': str(ex), 'values': [read_byte(buffer) for _ in range(trailing_bytes_length)]}})
        return buffer.tell() - start_buffer_cur

    @abstractmethod
    def _read_pixel(self, value: int) -> int:
        pass

    def save_converted(self, path: str):
        super().save_converted(path)
        colors = [self._read_pixel(self.bitmap_bytes[x * self.pixel_size:(x + 1) * self.pixel_size]).to_bytes(4, 'big')
                  for x in range(0, self.width * self.height)]
        colors = bytes().join(colors)
        img = Image.frombytes('RGBA', (self.width, self.height), colors)
        img.save(f'{path}.png')


class Bitmap8Bit(BaseBitmap):
    palette = None
    is_inline_palette = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.palette = None
        self.is_inline_palette = False

    # For textures in FAM files, inline palettes appear to be almost the same as parent palette,
    # sometimes better, sometime worse, the difference is not much noticeable.
    # In case of Autumn Valley fence texture it totally breaks the picture.
    # If ignore inline palettes in LN32 SHPI, DASH FSH will be broken ¯\_(ツ)_/¯
    # If ignore inline palette in all FAM textures, the train in alpine track will be broken ¯\_(ツ)_/¯
    # autumn valley fence texture broken only in ETRACKFM and NTRACKFM
    # FIXME find a generic solution to this problem
    @property
    def ignore_child_palette(self):
        try:
            return self.name == 'ga00' and self.parent.parent.parent.name == 'TR2_001.FAM'
        except:
            return False

    def _handle_trailing_bytes(self, buffer, trailing_bytes_length):
        from guess_parser import get_resource_class
        while trailing_bytes_length > 0:
            sub_resource = get_resource_class(buffer)
            assert isinstance(sub_resource, ReadBlockWrapper) and issubclass(sub_resource.block_class, BasePalette), f'Not a palette: {sub_resource.__class__.__name__}'
            trailing_bytes_length -= sub_resource.read(buffer, trailing_bytes_length)
            if not self.ignore_child_palette:
                self.palette = sub_resource
                self.is_inline_palette = True

    def _find_palettes(self, instance: BaseResource = None, recursive=True) -> List[ReadBlockWrapper]:
        if not instance:
            instance = self.parent
        own_palettes = [[x] if (isinstance(x, ReadBlockWrapper) and issubclass(x.block_class, BasePalette)) else self._find_palettes(x, recursive=False)
                        for i, x in enumerate(getattr(instance, 'resources', []))
                        if ((isinstance(x, ReadBlockWrapper) and issubclass(x.block_class, BasePalette)) or isinstance(instance, ArchiveResource))]
        own_palettes = [i for g in own_palettes for i in g]  # flatten
        own_palettes.reverse()  # invert, last palette more preferred
        if recursive and not own_palettes:
            if isinstance(instance, ResourceDirectory):
                for file_resource in instance.resources:
                    own_palettes.extend(self._find_palettes(file_resource, recursive=False))
            if not own_palettes and instance.parent:
                return self._find_palettes(instance.parent)
        return own_palettes

    # NFS 1 car texture have transparent tail lights
    @cached_property
    def is_tail_lights_texture_for_nfs1_car(self):
        from parsers.resources.archives import SHPIArchive
        from parsers.resources.geometries import OripGeometryResource
        return ((self.name in ['rsid', 'lite'])
                and isinstance(self.parent, SHPIArchive)
                and isinstance(self.parent.parent, OripGeometryResource)
                and self.parent.parent.is_car)

    def _read_pixel(self, value: bytes) -> int:
        if self.palette is None:
            palettes = self._find_palettes()
            self.palette = next((p for p in palettes if p.name != '!xxx'), None)
            if self.palette is None and len(palettes) > 0:
                self.palette = palettes[0]
        if self.palette is None:
            raise Exception('Palette not found for 8bit bitmap')
        index = int.from_bytes(value, byteorder='little')
        if index == 0xFE and self.is_tail_lights_texture_for_nfs1_car:
            return 0
        try:
            return self.palette.resource.colors[index]
        except IndexError:
            return 0

    def save_converted(self, path: str):
        super().save_converted(path)
        if settings.images__save_inline_palettes and self.is_inline_palette:
            self.palette.save_converted(path)


class Bitmap16Bit1555(BaseBitmap):
    pixel_size = 2

    def _read_pixel(self, value: bytes) -> int:
        color = int.from_bytes(value, byteorder='little')
        return transform_color_bitness(color, 1, 5, 5, 5)


class Bitmap16Bit0565(BaseBitmap):
    pixel_size = 2

    def _read_pixel(self, value: bytes) -> int:
        color = int.from_bytes(value, byteorder='little')
        return transform_color_bitness(color, 0, 5, 6, 5)


class Bitmap24Bit(BaseBitmap):
    pixel_size = 3

    def _read_pixel(self, value: bytes) -> int:
        color = int.from_bytes(value, byteorder='little')
        return color << 8 | 0xff


class Bitmap32Bit(BaseBitmap):
    pixel_size = 4

    def _read_pixel(self, value: bytes) -> int:
        color = int.from_bytes(value, byteorder='little')
        alpha = color & 0b11111111_00000000_00000000_00000000
        rgb = color & 0b00000000_11111111_11111111_11111111
        return rgb << 8 | alpha >> 24
