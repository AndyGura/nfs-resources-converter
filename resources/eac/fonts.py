from typing import Dict

from library.read_blocks import (IntegerBlock,
                                 UTF8Block,
                                 DeclarativeCompoundBlock,
                                 LengthPrefixedArrayBlock,
                                 AutoDetectBlock,
                                 BytesBlock,
                                 ArrayBlock,
                                 Padding,
                                 SubByteCompoundBlock,
                                 )
from library.read_blocks.misc.optional import OptionalBlock
from library.read_blocks.misc.value_validators import Or
from resources.eac.bitmaps import Bitmap4Bit, Bitmap8Bit
from resources.eac.fields.misc import Point2D


class GlyphDefinition(DeclarativeCompoundBlock):
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
        advance = (IntegerBlock(length=1),
                   {'description': 'Gap between this symbol and next one in rendered text'})
        x_offset = (IntegerBlock(length=1, is_signed=True),
                    {'description': 'Offset (x) for drawing the character image'})
        y_offset = (IntegerBlock(length=1, is_signed=True),
                    {'description': 'Offset (y) for drawing the character image'})
        num_kern = (OptionalBlock(child=IntegerBlock(length=1, is_signed=False),
                                  criteria=lambda ctx: ctx.data('../../version') >= 200),
                    {'description': 'Number of kerning pairs for this glyph'})
        kern_index = (OptionalBlock(child=IntegerBlock(length=2, is_signed=False),
                                    criteria=lambda ctx: ctx.data('../../flags/format') == '16-bytes'),
                      {'description': 'Index in kerning table?'})
        x_advance = (OptionalBlock(child=IntegerBlock(length=2, is_signed=False),
                                   criteria=lambda ctx: ctx.data('../../flags/format') == '16-bytes'),
                     {'description': 'Gap between this symbol and next one in rendered text?'})


class KerningItem(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        left = (IntegerBlock(length=1),
                {'description': 'Code of left glyph'})
        unk = (IntegerBlock(length=1))
        kerning = (IntegerBlock(length=1, is_signed=True))
        right = (IntegerBlock(length=1),
                 {'description': 'Code of right glyph'})


class FfnFont(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'serializable_to_disc': True,
            'hide_navigation_bar': True,
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (UTF8Block(length=4, value_validator=Or(['FNTF', 'FNTP', 'FNTS', 'FNTX', 'FNTM', 'FNTG', 'FNTA',
                                                               'FntF', 'FntP', 'FntS', 'FntX', 'FntM', 'FntG',
                                                               'FntA'])),
                       {'description': 'Resource ID'})
        block_size = (IntegerBlock(length=4,
                                   programmatic_value=lambda ctx: ctx.block.estimate_packed_size(ctx.get_full_data())),
                      {'description': 'The length of this FFN block in bytes'})
        version = IntegerBlock(length=2, is_signed=False)
        num_glyphs = (IntegerBlock(length=2,
                                   programmatic_value=lambda ctx: len(ctx.data('definitions'))),
                      {'description': 'Amount of symbols, defined in this font'})
        flags = SubByteCompoundBlock(length=4, schema=[
            (1, 'antialiased', 'boolean', [], ''),
            (1, 'dropshadow', 'boolean', [], ''),
            (1, 'outline', 'boolean', [], ''),
            (1, 'vram', 'boolean', [], ''),
            (2, 'baseline', 'enum', ['Roman (english)', 'Ideographic (Kanji)', 'Hanging (Arabic)', 'Unknown'], ''),
            (1, 'orientation', 'enum', ['Horizontal', 'Vertical'], ''),
            (1, 'direction', 'enum', ['LTR', 'RTL'], ''),
            (2, 'encoding', 'enum', ['ASCII', 'Unicode', 'Shift-JIS', 'Reserved'], ''),
            (1, 'format', 'enum', ['12-bytes', '16-bytes'], ''),
            (21, 'unk', 'number', [], ''),
        ])
        center = Point2D(child=IntegerBlock(length=1, is_signed=False))
        ascent = IntegerBlock(length=1, is_signed=False)
        descent = IntegerBlock(length=1, is_signed=False)
        definitions_ptr = (IntegerBlock(length=4,
                                        programmatic_value=lambda ctx: ctx.block.offset_to_child_when_packed(
                                            ctx.get_full_data(),
                                            'definitions')),
                           {'description': 'Pointer to definitions block'})
        kernings_ptr = (IntegerBlock(length=4,
                                     programmatic_value=lambda ctx: (
                                         0 if len(ctx.data('kenrings') == 0)
                                         else ctx.block.offset_to_child_when_packed(
                                             ctx.get_full_data(), 'kernings'))),
                        {'description': 'Pointer to kernings. 0 if there is no kernings table'})
        bdata_ptr = (IntegerBlock(length=4,
                                  programmatic_value=lambda ctx: ctx.block.offset_to_child_when_packed(
                                      ctx.get_full_data(),
                                      'bitmap')),
                     {'description': 'Pointer to bitmap block'})
        padding_0 = Padding(to=lambda ctx: ctx.data('definitions_ptr'))
        definitions = (ArrayBlock(child=GlyphDefinition(),
                                  length=lambda ctx: ctx.data('num_glyphs')),
                       {'description': 'Definitions of chars in this bitmap font'})
        padding_1 = OptionalBlock(child=Padding(to=lambda ctx: ctx.data('kernings_ptr')),
                                  criteria=lambda ctx: ctx.data('kernings_ptr') != 0)
        kernings = (OptionalBlock(child=LengthPrefixedArrayBlock(child=KerningItem(),
                                                                 length_block=IntegerBlock(length=4)),
                                  criteria=lambda ctx: ctx.data('kernings_ptr') != 0))
        padding_2 = Padding(to=lambda ctx: ctx.data('bdata_ptr'))
        bitmap = (AutoDetectBlock(possible_blocks=[Bitmap4Bit(), Bitmap8Bit()]),
                  {'description': 'Font atlas bitmap data',
                   'custom_offset': 'bdata_ptr'})
        remaining_bytes = (BytesBlock(length=(lambda ctx: ctx.read_bytes_remaining,
                                              'remaining bytes')),
                           {'is_unknown': True})

    def serializer_class(self):
        from serializers import FfnFontSerializer
        return FfnFontSerializer
