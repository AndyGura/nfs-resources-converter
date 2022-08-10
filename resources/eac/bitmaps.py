from library.read_blocks.array import ArrayBlock
from library.read_blocks.atomic import IntegerBlock
from library.read_blocks.compound import CompoundBlock
from library.helpers.exceptions import BlockIntegrityException
from library.read_blocks.literal import LiteralBlock
from library.read_blocks.sub_byte_array import SubByteArrayBlock
from library.utils import transform_bitness
from resources.eac import palettes
from resources.eac.fields.colors import (
    Color16Bit1555Block,
    Color16Bit0565Block,
    Color32BitBlock,
    Color24BitLittleEndianField
)


class AnyBitmapBlock(CompoundBlock):

    def _after_height_read(self, data, total_size, parent_read_data, state, **kwargs):
        pixel_size = self.instance_fields_map['bitmap'].child.static_size
        block_size = data['block_size'].value
        expected_block_size = pixel_size * data['width'].value * data['height'].value + 16
        if (parent_read_data and parent_read_data.get('shpi_directory') == 'WRAP') or block_size == 0:
            # TODO in WRAP directory there is no block size. What's there instead?
            # some NFS2 resources have block size equal to 0
            block_size = expected_block_size
        if block_size > total_size:
            raise BlockIntegrityException(f'Too big bitmap block size {block_size}, available: '
                                          f'{total_size}. Expected block size {expected_block_size}')
        if not state.get('trailing_bytes'):
            state['trailing_bytes'] = {}
        state['trailing_bytes']['length'] = block_size - expected_block_size
        if not state.get('bitmap'):
            state['bitmap'] = {}
        state['bitmap']['length'] = data['width'].value * data['height'].value


class Bitmap16Bit0565(AnyBitmapBlock, CompoundBlock):
    class Fields(CompoundBlock.Fields):
        resource_id = IntegerBlock(static_size=1, is_signed=False, required_value=0x78, description='Resource ID')
        block_size = IntegerBlock(static_size=3, is_signed=False, byte_order='little',
                                  description='Bitmap block size 16+2\\*width\\*height + trailing bytes length. For '
                                              '"WRAP" SHPI directory it contains some different unknown data')
        width = IntegerBlock(static_size=2, is_signed=False, byte_order='little', description='Bitmap width in pixels')
        height = IntegerBlock(static_size=2, is_signed=False, byte_order='little',
                              description='Bitmap height in pixels')
        unknowns = ArrayBlock(length=4, child=IntegerBlock(static_size=1))
        x = IntegerBlock(static_size=2, is_signed=False, byte_order='little',
                         description='X coordinate of bitmap position on screen. Used for menu/dash sprites')
        y = IntegerBlock(static_size=2, is_signed=False, byte_order='little',
                         description='Y coordinate of bitmap position on screen. Used for menu/dash sprites')
        bitmap = ArrayBlock(child=Color16Bit0565Block(), length_label='width * height',
                            description='Colors of bitmap pixels')
        trailing_bytes = ArrayBlock(child=IntegerBlock(static_size=1),
                                    length_label='block_size - (16 + 2\\*width\\*height)',
                                    description="Looks like aligning size to be divisible by 4")

        unknown_fields = ['unknowns', 'trailing_bytes']


class Bitmap4Bit(AnyBitmapBlock, CompoundBlock):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.block_description = 'Single-channel image, 4 bits per pixel. Used in FFN font files and some NFS2SE ' \
                                 'SHPI directories as some small sprites, like "dot". Seems to be always used as ' \
                                 'alpha channel, so we save it as white image with alpha mask'

    def _after_height_read(self, data, total_size, state, **kwargs):
        if not state.get('bitmap'):
            state['bitmap'] = {}
        state['bitmap']['length'] = data['width'].value * data['height'].value

    class Fields(CompoundBlock.Fields):
        resource_id = IntegerBlock(static_size=1, is_signed=False, required_value=0x7A, description='Resource ID')
        block_size = IntegerBlock(static_size=3, is_signed=False, byte_order='little',
                                  description='Bitmap block size 16+2\\*width\\*height + trailing bytes length. For '
                                              '"WRAP" SHPI directory it contains some different unknown data')
        width = IntegerBlock(static_size=2, is_signed=False, byte_order='little', description='Bitmap width in pixels')
        height = IntegerBlock(static_size=2, is_signed=False, byte_order='little',
                              description='Bitmap height in pixels')
        unknowns = ArrayBlock(length=4, child=IntegerBlock(static_size=1))
        x = IntegerBlock(static_size=2, is_signed=False, byte_order='little',
                         description='X coordinate of bitmap position on screen. Used for menu/dash sprites')
        y = IntegerBlock(static_size=2, is_signed=False, byte_order='little',
                         description='Y coordinate of bitmap position on screen. Used for menu/dash sprites')
        bitmap = SubByteArrayBlock(bits_per_value=4,
                                   length_label='width * height',
                                   value_deserialize_func=lambda x: 0xFFFFFF00 | transform_bitness(x, 4),
                                   value_serialize_func=lambda x: (x & 0xFF) >> 4,
                                   description='Font atlas bitmap data')

        unknown_fields = ['unknowns']


class Bitmap8Bit(AnyBitmapBlock, CompoundBlock):
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
        resource_id = IntegerBlock(static_size=1, is_signed=False, required_value=0x7B, description='Resource ID')
        block_size = IntegerBlock(static_size=3, is_signed=False, byte_order='little',
                                  description='Bitmap block size 16+2\\*width\\*height + trailing bytes length. For '
                                              '"WRAP" SHPI directory it contains some different unknown data')
        width = IntegerBlock(static_size=2, is_signed=False, byte_order='little', description='Bitmap width in pixels')
        height = IntegerBlock(static_size=2, is_signed=False, byte_order='little',
                              description='Bitmap height in pixels')
        unknowns = ArrayBlock(length=4, child=IntegerBlock(static_size=1))
        x = IntegerBlock(static_size=2, is_signed=False, byte_order='little',
                         description='X coordinate of bitmap position on screen. Used for menu/dash sprites')
        y = IntegerBlock(static_size=2, is_signed=False, byte_order='little',
                         description='Y coordinate of bitmap position on screen. Used for menu/dash sprites')
        bitmap = ArrayBlock(child=IntegerBlock(static_size=1, is_signed=False), length_label='width * height',
                            description='Color indexes of bitmap pixels. The actual colors are '
                                        'in assigned to this bitmap palette')
        trailing_bytes = ArrayBlock(child=IntegerBlock(static_size=1),
                                    length_label='block_size - (16 + width\\*height)',
                                    description="Looks like aligning size to be divisible by 4")
        palette = LiteralBlock(possible_resources=[palettes.PaletteReference(),
                                                   palettes.Palette24BitDos(),
                                                   palettes.Palette24Bit(),
                                                   palettes.Palette32Bit(),
                                                   palettes.Palette16Bit(),
                                                   ],
                               description='Palette, assigned to this bitmap or reference to external palette?. '
                                           'The exact mechanism of choosing the correct palette '
                                           '(except embedded one) is unknown')

        optional_fields = ['palette']
        unknown_fields = ['unknowns', 'trailing_bytes']


class Bitmap32Bit(AnyBitmapBlock, CompoundBlock):
    class Fields(CompoundBlock.Fields):
        resource_id = IntegerBlock(static_size=1, is_signed=False, required_value=0x7D, description='Resource ID')
        block_size = IntegerBlock(static_size=3, is_signed=False, byte_order='little',
                                  description='Bitmap block size 16+2\\*width\\*height + trailing bytes length. For '
                                              '"WRAP" SHPI directory it contains some different unknown data')
        width = IntegerBlock(static_size=2, is_signed=False, byte_order='little', description='Bitmap width in pixels')
        height = IntegerBlock(static_size=2, is_signed=False, byte_order='little',
                              description='Bitmap height in pixels')
        unknowns = ArrayBlock(length=4, child=IntegerBlock(static_size=1))
        x = IntegerBlock(static_size=2, is_signed=False, byte_order='little',
                         description='X coordinate of bitmap position on screen. Used for menu/dash sprites')
        y = IntegerBlock(static_size=2, is_signed=False, byte_order='little',
                         description='Y coordinate of bitmap position on screen. Used for menu/dash sprites')
        bitmap = ArrayBlock(child=Color32BitBlock(), length_label='width * height',
                            description='Colors of bitmap pixels')
        trailing_bytes = ArrayBlock(child=IntegerBlock(static_size=1),
                                    length_label='block_size - (16 + 4\\*width\\*height)',
                                    description="Looks like aligning size to be divisible by 4")

        unknown_fields = ['unknowns', 'trailing_bytes']


class Bitmap16Bit1555(AnyBitmapBlock, CompoundBlock):
    class Fields(CompoundBlock.Fields):
        resource_id = IntegerBlock(static_size=1, is_signed=False, required_value=0x7E, description='Resource ID')
        block_size = IntegerBlock(static_size=3, is_signed=False, byte_order='little',
                                  description='Bitmap block size 16+2\\*width\\*height + trailing bytes length. For '
                                              '"WRAP" SHPI directory it contains some different unknown data')
        width = IntegerBlock(static_size=2, is_signed=False, byte_order='little', description='Bitmap width in pixels')
        height = IntegerBlock(static_size=2, is_signed=False, byte_order='little',
                              description='Bitmap height in pixels')
        unknowns = ArrayBlock(length=4, child=IntegerBlock(static_size=1))
        x = IntegerBlock(static_size=2, is_signed=False, byte_order='little',
                         description='X coordinate of bitmap position on screen. Used for menu/dash sprites')
        y = IntegerBlock(static_size=2, is_signed=False, byte_order='little',
                         description='Y coordinate of bitmap position on screen. Used for menu/dash sprites')
        bitmap = ArrayBlock(child=Color16Bit1555Block(), length_label='width * height',
                            description='Colors of bitmap pixels')
        trailing_bytes = ArrayBlock(child=IntegerBlock(static_size=1),
                                    length_label='block_size - (16 + 2\\*width\\*height)',
                                    description="Looks like aligning size to be divisible by 4")

        unknown_fields = ['unknowns', 'trailing_bytes']


class Bitmap24Bit(AnyBitmapBlock, CompoundBlock):
    class Fields(CompoundBlock.Fields):
        resource_id = IntegerBlock(static_size=1, is_signed=False, required_value=0x7F, description='Resource ID')
        block_size = IntegerBlock(static_size=3, is_signed=False, byte_order='little',
                                  description='Bitmap block size 16+2\\*width\\*height + trailing bytes length. For '
                                              '"WRAP" SHPI directory it contains some different unknown data')
        width = IntegerBlock(static_size=2, is_signed=False, byte_order='little', description='Bitmap width in pixels')
        height = IntegerBlock(static_size=2, is_signed=False, byte_order='little',
                              description='Bitmap height in pixels')
        unknowns = ArrayBlock(length=4, child=IntegerBlock(static_size=1))
        x = IntegerBlock(static_size=2, is_signed=False, byte_order='little',
                         description='X coordinate of bitmap position on screen. Used for menu/dash sprites')
        y = IntegerBlock(static_size=2, is_signed=False, byte_order='little',
                         description='Y coordinate of bitmap position on screen. Used for menu/dash sprites')
        bitmap = ArrayBlock(child=Color24BitLittleEndianField(), length_label='width * height',
                            description='Colors of bitmap pixels')
        trailing_bytes = ArrayBlock(child=IntegerBlock(static_size=1),
                                    length_label='block_size - (16 + 3\\*width\\*height)',
                                    description="Looks like aligning size to be divisible by 4")

        unknown_fields = ['unknowns', 'trailing_bytes']
