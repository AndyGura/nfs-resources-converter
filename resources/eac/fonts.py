from typing import Dict

from library.read_blocks import IntegerBlock, UTF8Block, BytesBlock, ArrayBlock, DeclarativeCompoundBlock, \
    AutoDetectBlock, BitFlagsBlock, DelegateBlock
from library.read_blocks.misc.value_validators import Eq
from resources.eac.bitmaps import Bitmap4Bit, Bitmap8Bit
from resources.eac.fields.misc import Point2D


class GlyphDefinitionV1(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        code = (IntegerBlock(length=2),
                {'description': 'Code of symbol'})
        width = (IntegerBlock(length=1),
                 {'description': 'Width of symbol in font bitmap'})
        height = (IntegerBlock(length=1),
                  {'description': 'Height of symbol in font bitmap'})
        x = (IntegerBlock(length=2),
             {'description': 'Position (x) of symbol in font bitmap'})
        y = (IntegerBlock(length=2),
             {'description': 'Position (y) of symbol in font bitmap'})
        x_advance = (IntegerBlock(length=1),
                     {'description': 'Gap between this symbol and next one in rendered text'})
        x_offset = (IntegerBlock(length=1, is_signed=True),
                    {'description': 'Offset (x) for drawing the character image'})
        y_offset = (IntegerBlock(length=1, is_signed=True),
                    {'description': 'Offset (y) for drawing the character image'})


class GlyphDefinitionV2(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        code = (IntegerBlock(length=2),
                {'description': 'Code of symbol'})
        width = (IntegerBlock(length=1),
                 {'description': 'Width of symbol in font bitmap'})
        height = (IntegerBlock(length=1),
                  {'description': 'Height of symbol in font bitmap'})
        x = (IntegerBlock(length=2),
             {'description': 'Position (x) of symbol in font bitmap'})
        y = (IntegerBlock(length=2),
             {'description': 'Position (y) of symbol in font bitmap'})
        x_advance = (IntegerBlock(length=1),
                     {'description': 'Gap between this symbol and next one in rendered text'})
        x_offset = (IntegerBlock(length=1, is_signed=True),
                    {'description': 'Offset (x) for drawing the character image'})
        y_offset = (IntegerBlock(length=1, is_signed=True),
                    {'description': 'Offset (y) for drawing the character image'})
        num_kern = (IntegerBlock(length=1, is_signed=False),
                    {'description': 'Number of kerning pairs for this glyph?'})


class FfnFont(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'serializable_to_disc': True,
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (UTF8Block(length=4, value_validator=Eq('FNTF')),
                       {'description': 'Resource ID'})
        block_size = (IntegerBlock(length=4,
                                   programmatic_value=lambda ctx: ctx.block.estimate_packed_size(ctx.get_full_data())),
                      {'description': 'The length of this FFN block in bytes'})
        version = IntegerBlock(length=2, is_signed=False)
        num_glyphs = (IntegerBlock(length=2,
                                   programmatic_value=lambda ctx: len(ctx.data('definitions'))),
                      {'description': 'Amount of symbols, defined in this font'})
        flags = BitFlagsBlock(length=4, flag_names=[])
        center = Point2D(child=IntegerBlock(length=1, is_signed=False))
        ascent = IntegerBlock(length=1, is_signed=False)
        descent = IntegerBlock(length=1, is_signed=False)
        char_info_ptr = IntegerBlock(length=4)
        kerning_table_ptr = IntegerBlock(length=4)
        bdata_ptr = (IntegerBlock(length=4,
                                  programmatic_value=lambda ctx: ctx.block.offset_to_child_when_packed(
                                      ctx.get_full_data(),
                                      'bitmap')),
                     {'description': 'Pointer to bitmap block'})
        skip_bytes_0 = BytesBlock(length=(lambda ctx: ctx.data('char_info_ptr') - ctx.buffer.tell(),
                                          'up to offset char_info_ptr'))
        definitions = (DelegateBlock(possible_blocks=[ArrayBlock(child=GlyphDefinitionV1(),
                                                                 length=lambda ctx: ctx.data('num_glyphs')),
                                                      ArrayBlock(child=GlyphDefinitionV2(),
                                                                 length=lambda ctx: ctx.data('num_glyphs'))],
                                     choice_index=lambda ctx, **_: 1
                                     if ctx.data('version') >= 200
                                     else 0),
                       {'description': 'Definitions of chars in this bitmap font'})
        skip_bytes_1 = (BytesBlock(length=(lambda ctx: ctx.data('bdata_ptr') - ctx.buffer.tell(),
                                           'up to offset bdata_ptr')),
                        {'description': '4-bytes AD AD AD AD (optional, happens in nfs2 SWISS36)'})
        bitmap = (AutoDetectBlock(possible_blocks=[Bitmap4Bit(), Bitmap8Bit()]),
                  {'description': 'Font atlas bitmap data',
                   'custom_offset': 'bdata_ptr'})
        remaining_bytes = (BytesBlock(length=(lambda ctx: ctx.read_bytes_remaining,
                                              'remaining bytes')),
                           {'is_unknown': True})

    def serializer_class(self):
        from serializers import FfnFontSerializer
        return FfnFontSerializer
