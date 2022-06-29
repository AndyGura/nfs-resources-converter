from typing import Literal

from parsers.resources.utils import transform_bitness
from resources.basic.array_field import ArrayField
from resources.basic.atomic import IntegerField
from resources.basic.compound_block import CompoundBlock
from resources.basic.exceptions import BlockIntegrityException
from resources.basic.literal_block import LiteralResource
from resources.basic.sub_byte_array_field import SubByteArrayField
from resources.eac import palettes
from resources.eac.fields.colors import (
    Color16Bit1555Field,
    Color16Bit0565Field,
    Color32BitField,
    Color24BitLittleEndianField
)


class AnyBitmapResource(CompoundBlock):

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


class Bitmap16Bit0565(AnyBitmapResource, CompoundBlock):
    class Fields(CompoundBlock.Fields):
        resource_id = IntegerField(static_size=1, is_signed=False, required_value=0x78, description='Resource ID')
        block_size = IntegerField(static_size=3, is_signed=False, byte_order='little',
                                  description='Bitmap block size 16+2\\*width\\*height + trailing bytes length. For '
                                              '"WRAP" SHPI directory it contains some different unknown data')
        width = IntegerField(static_size=2, is_signed=False, byte_order='little', description='Bitmap width in pixels')
        height = IntegerField(static_size=2, is_signed=False, byte_order='little',
                              description='Bitmap height in pixels')
        unknowns = ArrayField(length=4, child=IntegerField(static_size=1), is_unknown=True)
        x = IntegerField(static_size=2, is_signed=False, byte_order='little',
                         description='X coordinate of bitmap position on screen. Used for menu/dash sprites')
        y = IntegerField(static_size=2, is_signed=False, byte_order='little',
                         description='Y coordinate of bitmap position on screen. Used for menu/dash sprites')
        bitmap = ArrayField(child=Color16Bit0565Field(), length_label='width * height',
                            description='Colors of bitmap pixels')
        trailing_bytes = ArrayField(child=IntegerField(static_size=1), is_unknown=True,
                                    length_label='block_size - (16 + 2\\*width\\*height)',
                                    description="Looks like aligning size to be divisible by 4")


class Bitmap4Bit(AnyBitmapResource, CompoundBlock):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.block_description = 'Single-channel image, 4 bits per pixel. Used in FFN font files and some NFS2SE ' \
                                 'SHPI directories as some small sprites, like "dot". Seems to be always used as ' \
                                 'alpha channel, so we save it as white image with alpha mask'

    def _after_height_read(self, data, total_size, **kwargs):
        self.instance_fields_map['bitmap'].length = data['width'] * data['height']

    class Fields(CompoundBlock.Fields):
        resource_id = IntegerField(static_size=1, is_signed=False, required_value=0x7A, description='Resource ID')
        block_size = IntegerField(static_size=3, is_signed=False, byte_order='little',
                                  description='Bitmap block size 16+2\\*width\\*height + trailing bytes length. For '
                                              '"WRAP" SHPI directory it contains some different unknown data')
        width = IntegerField(static_size=2, is_signed=False, byte_order='little', description='Bitmap width in pixels')
        height = IntegerField(static_size=2, is_signed=False, byte_order='little',
                              description='Bitmap height in pixels')
        unknowns = ArrayField(length=4, child=IntegerField(static_size=1), is_unknown=True)
        x = IntegerField(static_size=2, is_signed=False, byte_order='little',
                         description='X coordinate of bitmap position on screen. Used for menu/dash sprites')
        y = IntegerField(static_size=2, is_signed=False, byte_order='little',
                         description='Y coordinate of bitmap position on screen. Used for menu/dash sprites')
        bitmap = SubByteArrayField(bits_per_value=4,
                                   length_label='width * height',
                                   value_deserialize_func=lambda x: 0xFFFFFF00 | transform_bitness(x, 4),
                                   value_serialize_func=lambda x: (x & 0xFF) >> 4,
                                   description='Font atlas bitmap data')


class Bitmap8Bit(AnyBitmapResource, CompoundBlock):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.block_description = '8bit bitmap can be serialized to image only with palette. Basically, for every ' \
                                 'pixel it uses 8-bit index of color in assigned palette. The tricky part is to ' \
                                 'determine how the game understands which palette to use. In most cases, if bitmap ' \
                                 'has embedded palette, it should be used, EXCEPT Autumn Valley fence texture: there ' \
                                 'embedded palette should be ignored. In all other cases it is tricky even more: it ' \
                                 'uses !pal or !PAL palette from own SHPI archive, if it is WWWW archive, palette ' \
                                 'can be in a different SHPI before this one. In CONTROL directory most of QFS files ' \
                                 'use !pal even from different QFS file! It is a mystery how to reliably pick palette'

    class Fields(CompoundBlock.Fields):
        resource_id = IntegerField(static_size=1, is_signed=False, required_value=0x7B, description='Resource ID')
        block_size = IntegerField(static_size=3, is_signed=False, byte_order='little',
                                  description='Bitmap block size 16+2\\*width\\*height + trailing bytes length. For '
                                              '"WRAP" SHPI directory it contains some different unknown data')
        width = IntegerField(static_size=2, is_signed=False, byte_order='little', description='Bitmap width in pixels')
        height = IntegerField(static_size=2, is_signed=False, byte_order='little',
                              description='Bitmap height in pixels')
        unknowns = ArrayField(length=4, child=IntegerField(static_size=1), is_unknown=True)
        x = IntegerField(static_size=2, is_signed=False, byte_order='little',
                         description='X coordinate of bitmap position on screen. Used for menu/dash sprites')
        y = IntegerField(static_size=2, is_signed=False, byte_order='little',
                         description='Y coordinate of bitmap position on screen. Used for menu/dash sprites')
        bitmap = ArrayField(child=IntegerField(static_size=1, is_signed=False, ), length_label='width * height',
                            description='Color indexes of bitmap pixels. The actual colors are '
                                        'in assigned to this bitmap palette')
        trailing_bytes = ArrayField(child=IntegerField(static_size=1), is_unknown=True,
                                    length_label='block_size - (16 + width\\*height)',
                                    description="Looks like aligning size to be divisible by 4")
        palette = LiteralResource(possible_resources=[palettes.PaletteReference(),
                                                      palettes.Palette24BitDosResource(),
                                                      palettes.Palette24BitResource(),
                                                      palettes.Palette32BitResource(),
                                                      palettes.Palette16BitResource(),
                                                      ],
                                  description='Palette, assigned to this bitmap or reference to external palette?. '
                                              'The exact mechanism of choosing the correct palette '
                                              '(except embedded one) is unknown')

        optional_fields = ['palette']


class Bitmap32Bit(AnyBitmapResource, CompoundBlock):
    class Fields(CompoundBlock.Fields):
        resource_id = IntegerField(static_size=1, is_signed=False, required_value=0x7D, description='Resource ID')
        block_size = IntegerField(static_size=3, is_signed=False, byte_order='little',
                                  description='Bitmap block size 16+2\\*width\\*height + trailing bytes length. For '
                                              '"WRAP" SHPI directory it contains some different unknown data')
        width = IntegerField(static_size=2, is_signed=False, byte_order='little', description='Bitmap width in pixels')
        height = IntegerField(static_size=2, is_signed=False, byte_order='little',
                              description='Bitmap height in pixels')
        unknowns = ArrayField(length=4, child=IntegerField(static_size=1), is_unknown=True)
        x = IntegerField(static_size=2, is_signed=False, byte_order='little',
                         description='X coordinate of bitmap position on screen. Used for menu/dash sprites')
        y = IntegerField(static_size=2, is_signed=False, byte_order='little',
                         description='Y coordinate of bitmap position on screen. Used for menu/dash sprites')
        bitmap = ArrayField(child=Color32BitField(), length_label='width * height',
                            description='Colors of bitmap pixels')
        trailing_bytes = ArrayField(child=IntegerField(static_size=1), is_unknown=True,
                                    length_label='block_size - (16 + 4\\*width\\*height)',
                                    description="Looks like aligning size to be divisible by 4")


class Bitmap16Bit1555(AnyBitmapResource, CompoundBlock):
    class Fields(CompoundBlock.Fields):
        resource_id = IntegerField(static_size=1, is_signed=False, required_value=0x7E, description='Resource ID')
        block_size = IntegerField(static_size=3, is_signed=False, byte_order='little',
                                  description='Bitmap block size 16+2\\*width\\*height + trailing bytes length. For '
                                              '"WRAP" SHPI directory it contains some different unknown data')
        width = IntegerField(static_size=2, is_signed=False, byte_order='little', description='Bitmap width in pixels')
        height = IntegerField(static_size=2, is_signed=False, byte_order='little',
                              description='Bitmap height in pixels')
        unknowns = ArrayField(length=4, child=IntegerField(static_size=1), is_unknown=True)
        x = IntegerField(static_size=2, is_signed=False, byte_order='little',
                         description='X coordinate of bitmap position on screen. Used for menu/dash sprites')
        y = IntegerField(static_size=2, is_signed=False, byte_order='little',
                         description='Y coordinate of bitmap position on screen. Used for menu/dash sprites')
        bitmap = ArrayField(child=Color16Bit1555Field(), length_label='width * height',
                            description='Colors of bitmap pixels')
        trailing_bytes = ArrayField(child=IntegerField(static_size=1), is_unknown=True,
                                    length_label='block_size - (16 + 2\\*width\\*height)',
                                    description="Looks like aligning size to be divisible by 4")


class Bitmap24Bit(AnyBitmapResource, CompoundBlock):
    class Fields(CompoundBlock.Fields):
        resource_id = IntegerField(static_size=1, is_signed=False, required_value=0x7F, description='Resource ID')
        block_size = IntegerField(static_size=3, is_signed=False, byte_order='little',
                                  description='Bitmap block size 16+2\\*width\\*height + trailing bytes length. For '
                                              '"WRAP" SHPI directory it contains some different unknown data')
        width = IntegerField(static_size=2, is_signed=False, byte_order='little', description='Bitmap width in pixels')
        height = IntegerField(static_size=2, is_signed=False, byte_order='little',
                              description='Bitmap height in pixels')
        unknowns = ArrayField(length=4, child=IntegerField(static_size=1), is_unknown=True)
        x = IntegerField(static_size=2, is_signed=False, byte_order='little',
                         description='X coordinate of bitmap position on screen. Used for menu/dash sprites')
        y = IntegerField(static_size=2, is_signed=False, byte_order='little',
                         description='Y coordinate of bitmap position on screen. Used for menu/dash sprites')
        bitmap = ArrayField(child=Color24BitLittleEndianField(), length_label='width * height',
                            description='Colors of bitmap pixels')
        trailing_bytes = ArrayField(child=IntegerField(static_size=1), is_unknown=True,
                                    length_label='block_size - (16 + 3\\*width\\*height)',
                                    description="Looks like aligning size to be divisible by 4")
