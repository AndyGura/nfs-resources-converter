from abc import ABC, abstractmethod
from functools import cached_property
from io import BufferedReader, SEEK_CUR
from typing import List

from PIL import Image

from buffer_utils import read_short, read_3int
from parsers.resources.base import BaseResource
from parsers.resources.collections import ResourceDirectory, ArchiveResource
from parsers.resources.palettes import BasePalette
from parsers.resources.utils import transform_color_bitness


class BaseBitmap(BaseResource, ABC):
    pixel_size = 1
    bitmap_bytes = None

    def _get_directory_identifier(self):
        from parsers.resources.archives import SHPIArchive
        entity = self
        while entity and not isinstance(entity, SHPIArchive):
            entity = entity.parent
        return entity and entity.directory_identifier

    def read(self, buffer: BufferedReader, length: int, path: str = None) -> int:
        buffer.seek(1, SEEK_CUR)  # bitmap type byte
        block_size = read_3int(buffer)
        self.width = read_short(buffer)
        self.height = read_short(buffer)
        # TODO in WRAP directory there is no block size. What's there instead?
        directory_identifier = self._get_directory_identifier()
        if directory_identifier == 'LN32':
            assert block_size == self.pixel_size * self.width * self.height + 16, \
                f'Not expected bitmap block size {block_size}. Expected {self.pixel_size * self.width * self.height}'
        else:
            block_size = self.pixel_size * self.width * self.height + 16
        if self.width > 8192 or self.height > 8192:
            raise Exception(f'Suspiciously large bitmap {self.width}/{self.height}')
        buffer.seek(4, SEEK_CUR)  # unknown bytes :(
        # position on screen
        self.x = read_short(buffer)
        self.y = read_short(buffer)
        self.bitmap_bytes = buffer.read(block_size - 16)
        return block_size

    @abstractmethod
    def _read_pixel(self, value: int) -> int:
        pass

    def save_converted(self, path: str):
        colors = [self._read_pixel(self.bitmap_bytes[x * self.pixel_size:(x + 1) * self.pixel_size]).to_bytes(4, 'big')
                  for x in range(0, self.width * self.height)]
        colors = bytes().join(colors)
        img = Image.frombytes('RGBA', (self.width, self.height), colors)
        img.save(f'{path}.png')
        for resource in self.resources:
            resource.save_converted(f"{path}.{resource.name.replace('/', '_')}")


class Bitmap8Bit(BaseBitmap):
    palette = None

    def find_palettes(self, instance: BaseResource, recursive=True) -> List[BasePalette]:
        own_palettes = [[x] if isinstance(x, BasePalette) else self.find_palettes(x, recursive=False)
                        for i, x in enumerate(instance.resources)
                        if (isinstance(x, BasePalette) or isinstance(instance, ArchiveResource))]
        own_palettes = [i for g in own_palettes for i in g]  # flatten
        own_palettes.reverse() # invert, last palette more preferred
        if recursive and not own_palettes:
            if isinstance(instance, ResourceDirectory):
                for file_resource in instance.resources:
                    own_palettes.extend(self.find_palettes(file_resource, recursive=False))
            if not own_palettes and instance.parent:
                return self.find_palettes(instance.parent)
        return own_palettes

    # NFS 1 car texture have transparent tail lights
    @cached_property
    def is_tail_lights_texture_for_nfs1_car(self):
        from parsers.resources.archives import SHPIArchive
        from parsers.resources.geometries import OripGeometryResource
        return (self.name == 'rsid'
                and isinstance(self.parent, SHPIArchive)
                and isinstance(self.parent.parent, OripGeometryResource)
                and self.parent.parent.is_car)

    def _read_pixel(self, value: bytes) -> int:
        if self.palette is None:
            palettes = self.find_palettes(self)
            self.palette = next((p for p in palettes if p.name != '!xxx'), None)
            if self.palette is None and len(palettes) > 0:
                self.palette = palettes[0]
        if self.palette is None:
            raise Exception('Palette not found for 8bit bitmap')
        index = int.from_bytes(value, byteorder='little')
        if index == 0xFE and self.is_tail_lights_texture_for_nfs1_car:
            return 0
        return self.palette.get_color(index)


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
