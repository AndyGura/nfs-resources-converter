from typing import Dict

from library.read_blocks import (DeclarativeCompoundBlock,
                                 IntegerBlock,
                                 SubByteArrayBlock,
                                 BytesBlock,
                                 ArrayBlock)
from library.read_blocks.misc.value_validators import Eq
from library.utils import transform_bitness
from resources.eac.fields.colors import (
    Color16Bit1555Block,
    Color16Bit0565Block,
    Color32BitBlock,
    Color24BitLittleEndianField
)


class AnyBitmapBlock(DeclarativeCompoundBlock):

    def serializer_class(self):
        from serializers import BitmapSerializer
        return BitmapSerializer


class Bitmap16Bit0565(AnyBitmapBlock, DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (IntegerBlock(length=1, value_validator=Eq(0x78)),
                       {'description': 'Resource ID'})
        block_size = (IntegerBlock(length=3),
                      {'description': 'Bitmap block size 16+2\\*width\\*height + trailing bytes length'})
        width = (IntegerBlock(length=2),
                 {'description': 'Bitmap width in pixels'})
        height = (IntegerBlock(length=2),
                  {'description': 'Bitmap height in pixels'})
        unk = (BytesBlock(length=4),
               {'is_unknown': True})
        x = (IntegerBlock(length=2),
             {'description': 'X coordinate of bitmap position on screen. Used for menu/dash sprites'})
        y = (IntegerBlock(length=2),
             {'description': 'Y coordinate of bitmap position on screen. Used for menu/dash sprites'})
        bitmap = (ArrayBlock(child=Color16Bit0565Block(simplified=True),
                             length=lambda ctx: ctx.data('width') * ctx.data('height')),
                  {'description': 'Colors of bitmap pixels'})


class Bitmap4Bit(AnyBitmapBlock, DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Single-channel image, 4 bits per pixel. Used in FFN font files and some NFS2SE ' \
                                 'SHPI directories as some small sprites, like "dot". Seems to be always used as ' \
                                 'alpha channel, so we save it as white image with alpha mask',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (IntegerBlock(length=1, value_validator=Eq(0x7A)),
                       {'description': 'Resource ID'})
        block_size = (IntegerBlock(length=3),
                      {'description': 'Bitmap block size 16+width\\*height/2 + trailing bytes length'})
        width = (IntegerBlock(length=2),
                 {'description': 'Bitmap width in pixels. Has to be an even number (at least in the FFN font)'})
        height = (IntegerBlock(length=2),
                  {'description': 'Bitmap height in pixels'})
        unk = (BytesBlock(length=4),
               {'is_unknown': True})
        x = (IntegerBlock(length=2),
             {'description': 'X coordinate of bitmap position on screen. Used for menu/dash sprites'})
        y = (IntegerBlock(length=2),
             {'description': 'Y coordinate of bitmap position on screen. Used for menu/dash sprites'})
        bitmap = (ArrayBlock(length=lambda ctx: ctx.data('height'),
                             child=SubByteArrayBlock(bits_per_value=4,
                                                     length=lambda ctx: ctx.data('../width'),
                                                     value_deserialize_func=lambda x: 0xFFFFFF00
                                                                                      | transform_bitness(x, 4),
                                                     value_serialize_func=lambda x: (x & 0xFF) >> 4)),
                  {'description': 'Font atlas bitmap data, array of bitmap rows'})


class Bitmap8Bit(AnyBitmapBlock, DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': '8bit bitmap can be serialized to image only with palette. Basically, for every '
                                 'pixel it uses 8-bit index of color in assigned palette. The tricky part is to '
                                 'determine how the game understands which palette to use. In most cases, if bitmap '
                                 'has embedded palette, it should be used, EXCEPT Autumn Valley fence texture: there '
                                 'embedded palette should be ignored. In all other cases it is tricky even more: it '
                                 'uses !pal or !PAL palette from own SHPI archive, if it is WWWW archive, palette '
                                 'can be in a different SHPI before this one. In CONTROL directory most of QFS files '
                                 'use !pal even from different QFS file! It is a mystery how to reliably pick palette',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (IntegerBlock(length=1, value_validator=Eq(0x7B)),
                       {'description': 'Resource ID'})
        block_size = (IntegerBlock(length=3),
                      {'description': 'Bitmap block size 16+width\\*height + trailing bytes length'})
        width = (IntegerBlock(length=2),
                 {'description': 'Bitmap width in pixels'})
        height = (IntegerBlock(length=2),
                  {'description': 'Bitmap height in pixels'})
        unk = (IntegerBlock(length=2),
               {'is_unknown': True})
        pivot_y = (IntegerBlock(length=2),
                   {'description': 'For "horz" bitmap in TNFS FAM files: Y coordinate of the horizon line on '
                                   'the image. Higher value = image as horizon will be put higher on the screen. '
                                   'Seems to affect only open tracks'})
        x = (IntegerBlock(length=2),
             {'description': 'X coordinate of bitmap position on screen. Used for menu/dash sprites'})
        y = (IntegerBlock(length=2),
             {'description': 'Y coordinate of bitmap position on screen. Used for menu/dash sprites'})
        bitmap = (ArrayBlock(child=IntegerBlock(length=1),
                             length=lambda ctx: ctx.data('width') * ctx.data('height')),
                  {'description': 'Color indexes of bitmap pixels. The actual colors are '
                                  'in assigned to this bitmap palette'})

    def serializer_class(self):
        from serializers import BitmapWithPaletteSerializer
        return BitmapWithPaletteSerializer


class Bitmap32Bit(AnyBitmapBlock, DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (IntegerBlock(length=1, value_validator=Eq(0x7D)),
                       {'description': 'Resource ID'})
        block_size = (IntegerBlock(length=3),
                      {'description': 'Bitmap block size 16+4\\*width\\*height + trailing bytes length'})
        width = (IntegerBlock(length=2),
                 {'description': 'Bitmap width in pixels'})
        height = (IntegerBlock(length=2),
                  {'description': 'Bitmap height in pixels'})
        unk = (BytesBlock(length=4),
               {'is_unknown': True})
        x = (IntegerBlock(length=2),
             {'description': 'X coordinate of bitmap position on screen. Used for menu/dash sprites'})
        y = (IntegerBlock(length=2),
             {'description': 'Y coordinate of bitmap position on screen. Used for menu/dash sprites'})
        bitmap = (ArrayBlock(child=Color32BitBlock(),
                             length=lambda ctx: ctx.data('width') * ctx.data('height')),
                  {'description': 'Colors of bitmap pixels'})


class Bitmap16Bit1555(AnyBitmapBlock, DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (IntegerBlock(length=1, value_validator=Eq(0x7E)),
                       {'description': 'Resource ID'})
        block_size = (IntegerBlock(length=3),
                      {'description': 'Bitmap block size 16+2\\*width\\*height + trailing bytes length'})
        width = (IntegerBlock(length=2),
                 {'description': 'Bitmap width in pixels'})
        height = (IntegerBlock(length=2),
                  {'description': 'Bitmap height in pixels'})
        unk = (BytesBlock(length=4),
               {'is_unknown': True})
        x = (IntegerBlock(length=2),
             {'description': 'X coordinate of bitmap position on screen. Used for menu/dash sprites'})
        y = (IntegerBlock(length=2),
             {'description': 'Y coordinate of bitmap position on screen. Used for menu/dash sprites'})
        bitmap = (ArrayBlock(child=Color16Bit1555Block(),
                             length=lambda ctx: ctx.data('width') * ctx.data('height')),
                  {'description': 'Colors of bitmap pixels'})


class Bitmap24Bit(AnyBitmapBlock, DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (IntegerBlock(length=1, value_validator=Eq(0x7F)),
                       {'description': 'Resource ID'})
        block_size = (IntegerBlock(length=3),
                      {'description': 'Bitmap block size 16+3\\*width\\*height + trailing bytes length'})
        width = (IntegerBlock(length=2),
                 {'description': 'Bitmap width in pixels'})
        height = (IntegerBlock(length=2),
                  {'description': 'Bitmap height in pixels'})
        unk = (BytesBlock(length=4),
               {'is_unknown': True})
        x = (IntegerBlock(length=2),
             {'description': 'X coordinate of bitmap position on screen. Used for menu/dash sprites'})
        y = (IntegerBlock(length=2),
             {'description': 'Y coordinate of bitmap position on screen. Used for menu/dash sprites'})
        bitmap = (ArrayBlock(child=Color24BitLittleEndianField(),
                             length=lambda ctx: ctx.data('width') * ctx.data('height')),
                  {'description': 'Colors of bitmap pixels'})
