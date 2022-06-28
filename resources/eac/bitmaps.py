from math import ceil
from typing import Literal

from exceptions import BlockIntegrityException
from resources.base import BaseResource, LiteralResource
from resources.eac import palettes
from resources.fields import Int3Field, Int2Field, ArrayField, ByteField
from resources.fields.colors import (
    Color16Bit1555Field,
    Color16Bit0565Field,
    Color32BitField,
    Color24BitLittleEndianField
)


class AnyBitmapResource(BaseResource):

    def __init__(self, shpi_directory_identifier: Literal["LN32", "WRAP", "GIMX"] = None, **kwargs):
        super(AnyBitmapResource, self).__init__(shpi_directory_identifier=shpi_directory_identifier,
                                                **kwargs)
        self.shpi_directory_identifier = shpi_directory_identifier

    def _after_height_read(self, data, total_size, **kwargs):
        pixel_size = self.instance_fields_map['bitmap'].child.size
        block_size = data['block_size']
        expected_block_size = pixel_size * data['width'] * data['height'] + 16
        if self.shpi_directory_identifier == 'WRAP' or block_size == 0:
            # TODO in WRAP directory there is no block size. What's there instead?
            # some NFS2 resources have block size equal to 0
            block_size = expected_block_size
        if block_size > total_size:
            raise BlockIntegrityException(f'Too big bitmap block size {block_size}, available: '
                                          f'{total_size}. Expected block size {expected_block_size}')
        self.instance_fields_map['trailing_bytes'].length = block_size - expected_block_size
        self.instance_fields_map['bitmap'].length = data['width'] * data['height']


class Bitmap16Bit0565(AnyBitmapResource, BaseResource):
    class Fields(BaseResource.Fields):
        resource_id = ByteField(required_value=0x78, description='Resource ID')
        block_size = Int3Field(description='Bitmap block size 16+2\\*width\\*height + trailing bytes length. For '
                                           '"WRAP" SHPI directory it contains some different unknown data')
        width = Int2Field(description='Bitmap width in pixels')
        height = Int2Field(description='Bitmap height in pixels')
        unknowns = ArrayField(length=4, child=ByteField(), is_unknown=True)
        x = Int2Field(description='X coordinate of bitmap position on screen. Used for menu/dash sprites')
        y = Int2Field(description='Y coordinate of bitmap position on screen. Used for menu/dash sprites')
        bitmap = ArrayField(child=Color16Bit0565Field(), length_label='width * height',
                            description='Colors of bitmap pixels')
        trailing_bytes = ArrayField(child=ByteField(), is_unknown=True,
                                    length_label='block_size - (16 + 2\\*width\\*height)',
                                    description="Looks like aligning size to be divisible by 4")


class Bitmap4Bit(AnyBitmapResource, BaseResource):
    block_description = 'Grayscale image, 4 bits per pixel. Used in FFN font files. In some of NFS2SE SHPI ' \
                        'directories there is an image with the same signature named "dot", but they do not work: ' \
                        'size 36x1536 == 27648 bytes, but available is only 100 for entire block (87 without header)'

    def _after_height_read(self, data, total_size, **kwargs):
        self.instance_fields_map['bitmap'].length = ceil(data['width'] * data['height'] / 2)

    class Fields(BaseResource.Fields):
        resource_id = ByteField(required_value=0x7A, description='Resource ID')
        width = Int2Field(description='Bitmap width in pixels')
        height = Int2Field(description='Bitmap height in pixels')
        unknowns = ArrayField(length=8, child=ByteField(), is_unknown=True)
        bitmap = ArrayField(length_label='width * height / 2', child=ByteField(),
                            description='Font atlas bitmap data')  # TODO bit array


class Bitmap8Bit(AnyBitmapResource, BaseResource):
    block_description = '8bit bitmap can be serialized to image only with palette. Basically, for every pixel it uses ' \
                        '8-bit index of color in assigned palette. The tricky part is to determine how the game ' \
                        'understands which palette to use. In most cases, if bitmap has embedded palette, it should be used, ' \
                        'EXCEPT Autumn Valley fence texture: there embedded palette should be ignored. In all other cases it ' \
                        'is tricky even more: it uses !pal or !PAL palette from own SHPI archive, if it is WWWW archive, ' \
                        'palette can be in a different SHPI before this one. In CONTROL directory most of QFS files ' \
                        'use !pal even from different QFS file! It is a mystery how to reliably pick needed palette'

    class Fields(BaseResource.Fields):
        resource_id = ByteField(required_value=0x7B, description='Resource ID')
        block_size = Int3Field(description='Bitmap block size 16+2\\*width\\*height + trailing bytes length. For '
                                           '"WRAP" SHPI directory it contains some different unknown data')
        width = Int2Field(description='Bitmap width in pixels')
        height = Int2Field(description='Bitmap height in pixels')
        unknowns = ArrayField(length=4, child=ByteField(), is_unknown=True)
        x = Int2Field(description='X coordinate of bitmap position on screen. Used for menu/dash sprites')
        y = Int2Field(description='Y coordinate of bitmap position on screen. Used for menu/dash sprites')
        bitmap = ArrayField(child=ByteField(), length_label='width * height',
                            description='Color indexes of bitmap pixels. The actual colors are '
                                        'in assigned to this bitmap palette')
        trailing_bytes = ArrayField(child=ByteField(), is_unknown=True,
                                    length_label='block_size - (16 + width\\*height)',
                                    description="Looks like aligning size to be divisible by 4")
        palette = LiteralResource(possible_resources=[palettes.PaletteReference(),
                                                      palettes.Palette24BitDosResource(),
                                                      palettes.Palette24BitResource(),
                                                      palettes.Palette32BitResource(),
                                                      palettes.Palette16BitResource(),
                                                      ],
                                  is_optional=True,
                                  description='Palette, assigned to this bitmap or reference to external palette?. '
                                              'The exact mechanism of choosing the correct palette '
                                              '(except embedded one) is unknown')


class Bitmap32Bit(AnyBitmapResource, BaseResource):
    class Fields(BaseResource.Fields):
        resource_id = ByteField(required_value=0x7D, description='Resource ID')
        block_size = Int3Field(description='Bitmap block size 16+2\\*width\\*height + trailing bytes length. For '
                                           '"WRAP" SHPI directory it contains some different unknown data')
        width = Int2Field(description='Bitmap width in pixels')
        height = Int2Field(description='Bitmap height in pixels')
        unknowns = ArrayField(length=4, child=ByteField(), is_unknown=True)
        x = Int2Field(description='X coordinate of bitmap position on screen. Used for menu/dash sprites')
        y = Int2Field(description='Y coordinate of bitmap position on screen. Used for menu/dash sprites')
        bitmap = ArrayField(child=Color32BitField(), length_label='width * height',
                            description='Colors of bitmap pixels')
        trailing_bytes = ArrayField(child=ByteField(), is_unknown=True,
                                    length_label='block_size - (16 + 4\\*width\\*height)',
                                    description="Looks like aligning size to be divisible by 4")


class Bitmap16Bit1555(AnyBitmapResource, BaseResource):
    class Fields(BaseResource.Fields):
        resource_id = ByteField(required_value=0x7E, description='Resource ID')
        block_size = Int3Field(description='Bitmap block size 16+2\\*width\\*height + trailing bytes length. For '
                                           '"WRAP" SHPI directory it contains some different unknown data')
        width = Int2Field(description='Bitmap width in pixels')
        height = Int2Field(description='Bitmap height in pixels')
        unknowns = ArrayField(length=4, child=ByteField(), is_unknown=True)
        x = Int2Field(description='X coordinate of bitmap position on screen. Used for menu/dash sprites')
        y = Int2Field(description='Y coordinate of bitmap position on screen. Used for menu/dash sprites')
        bitmap = ArrayField(child=Color16Bit1555Field(), length_label='width * height',
                            description='Colors of bitmap pixels')
        trailing_bytes = ArrayField(child=ByteField(), is_unknown=True,
                                    length_label='block_size - (16 + 2\\*width\\*height)',
                                    description="Looks like aligning size to be divisible by 4")


class Bitmap24Bit(AnyBitmapResource, BaseResource):
    class Fields(BaseResource.Fields):
        resource_id = ByteField(required_value=0x7F, description='Resource ID')
        block_size = Int3Field(description='Bitmap block size 16+2\\*width\\*height + trailing bytes length. For '
                                           '"WRAP" SHPI directory it contains some different unknown data')
        width = Int2Field(description='Bitmap width in pixels')
        height = Int2Field(description='Bitmap height in pixels')
        unknowns = ArrayField(length=4, child=ByteField(), is_unknown=True)
        x = Int2Field(description='X coordinate of bitmap position on screen. Used for menu/dash sprites')
        y = Int2Field(description='Y coordinate of bitmap position on screen. Used for menu/dash sprites')
        bitmap = ArrayField(child=Color24BitLittleEndianField(), length_label='width * height',
                            description='Colors of bitmap pixels')
        trailing_bytes = ArrayField(child=ByteField(), is_unknown=True,
                                    length_label='block_size - (16 + 3\\*width\\*height)',
                                    description="Looks like aligning size to be divisible by 4")
