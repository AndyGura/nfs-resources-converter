from typing import Dict

from library.context import ReadContext
from library.read_blocks import (IntegerBlock,
                                 UTF8Block,
                                 DeclarativeCompoundBlock,
                                 LengthPrefixedArrayBlock,
                                 BytesBlock,
                                 ArrayBlock,
                                 Padding,
                                 SubByteCompoundBlock,
                                 OptionalBlock,
                                 )
from library.read_blocks.misc.value_validators import Or
from resources.eac.bitmaps import EacImage
from resources.eac.fields.misc import Point2D


class GlyphDefinition(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'description': 'Glyph definition.<br/>'
                           '- for FNT version < 200 has length 11 bytes.<br/>'
                           '- for versions >= 200 and <= 309 - 12 bytes, last byte is padding.<br/>'
                           '- for versions > 309 - 12th byte is num_kern.<br/>'
                           '- for versions >= 321 it may be 16 bytes if "format" flag is set to 16-bytes',
        }

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
        # 12-th byte
        num_kern = (OptionalBlock(child=IntegerBlock(length=1, is_signed=False,
                                                     programmatic_value=lambda ctx: sum(
                                                         1 for x in ctx.data('../../kernings') if
                                                         x['right'] == ctx.data('code'))),
                                  criteria=lambda ctx: ctx.data('../../version') > 309),
                    {'description': 'Number of kerning pairs for this glyph'})
        pad = (OptionalBlock(child=IntegerBlock(length=1, is_signed=False),
                             criteria=lambda ctx: 200 <= ctx.data('../../version') <= 309),
               {'description': 'Padding'})
        # 13th - 16th bytes
        kern_index = (OptionalBlock(child=IntegerBlock(length=2, is_signed=False),
                                    criteria=lambda ctx: ctx.data('../../version') >= 321 and ctx.data(
                                        '../../flags/format') == '16-bytes'),
                      {'description': 'Index in kerning table?'})
        x_advance = (OptionalBlock(child=IntegerBlock(length=2, is_signed=False),
                                   criteria=lambda ctx: ctx.data('../../version') >= 321 and ctx.data(
                                       '../../flags/format') == '16-bytes'),
                     {'description': 'Gap between this symbol and next one in rendered text?'})

    def new_data(self):
        data = super().new_data()
        data['width'] = 1
        data['height'] = 1
        return data


class KerningItem(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        left = (IntegerBlock(length=2),
                {'description': 'Code of left glyph'})
        kerning = (IntegerBlock(length=1, is_signed=True))
        right = (IntegerBlock(length=1),
                 {'description': 'Code of right glyph'})


def _block_size_delta(ctx):
    if ctx.data('version') <= 101:
        return len(ctx.data('padding_2'))
    else:
        return 0


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
                                   programmatic_value=lambda ctx: ctx.block.estimate_packed_size(ctx.get_full_data())
                                                                  - len(ctx.data('remaining_bytes'))
                                                                  - _block_size_delta(ctx)),
                      {'usage': 'io,doc',
                       'description': 'The length of this FFN block in bytes. Does not include "remaining_bytes" '
                                      'length. For older versions (I set version <= 101, but it can be anywhere < 309), '
                                      '"padding_2" length is not included as well'})
        version = IntegerBlock(length=2, is_signed=False)
        num_glyphs = (IntegerBlock(length=2,
                                   programmatic_value=lambda ctx: len(ctx.data('definitions'))),
                      {'usage': 'io,doc',
                       'description': 'Amount of symbols, defined in this font'})
        flags = SubByteCompoundBlock(length=4, schema=[
            (13, 'pad', 'number', [], 'pad structure to 32 bits'),
            (1, 'format', 'enum', ['12-bytes', '16-bytes'], ''),
            (2, 'encoding', 'enum', ['ASCII', 'Unicode', 'Shift-JIS', 'Reserved'], ''),
            (4, 'layoutpad', 'number', [], 'pad to save 4 other layout bits'),
            (1, 'direction', 'enum', ['LTR', 'RTL'], ''),
            (1, 'orientation', 'enum', ['Horizontal', 'Vertical'], ''),
            (2, 'baseline', 'enum', ['Roman (english)', 'Ideographic (Kanji)', 'Hanging (Arabic)', 'Unknown'], ''),
            (4, 'drawpad', 'number', [], 'pad to save 4 other draw attribute bits'),
            (1, 'vram', 'boolean', [],
             'VRAM fonts are the default, they have extra space around the characters so that uv extraction will work under hardware.'),
            (1, 'outline', 'boolean', [], ''),
            (1, 'dropshadow', 'boolean', [], ''),
            (1, 'antialiased', 'boolean', [], ''),
        ])
        center = Point2D(child=IntegerBlock(length=1, is_signed=False))
        ascent = IntegerBlock(length=1, is_signed=False)
        descent = IntegerBlock(length=1, is_signed=False)
        definitions_ptr = (IntegerBlock(length=4,
                                        programmatic_value=lambda ctx: ctx.block.offset_to_child_when_packed(
                                            ctx.get_full_data(),
                                            'definitions')),
                           {'usage': 'io,doc',
                            'description': 'Pointer to definitions block'})
        kernings_ptr = (IntegerBlock(length=4,
                                     programmatic_value=lambda ctx: (
                                         0 if len(ctx.data('kernings')) == 0
                                         else ctx.block.offset_to_child_when_packed(
                                             ctx.get_full_data(), 'kernings'))),
                        {'usage': 'io,doc',
                         'description': 'Pointer to kernings. 0 if there is no kernings table'})
        bdata_ptr = (IntegerBlock(length=4,
                                  programmatic_value=lambda ctx: ctx.block.offset_to_child_when_packed(
                                      ctx.get_full_data(),
                                      'bitmap')),
                     {'usage': 'io,doc',
                      'description': 'Pointer to bitmap block'})
        padding_0 = (Padding(to=lambda ctx: ctx.data('definitions_ptr')),
                     {'is_unknown': True})
        definitions = (ArrayBlock(child=GlyphDefinition(),
                                  length=lambda ctx: ctx.data('num_glyphs')),
                       {'description': 'Definitions of chars in this bitmap font'})
        padding_1 = (OptionalBlock(child=Padding(to=lambda ctx: ctx.data('kernings_ptr')),
                                   criteria=lambda ctx: ctx.data('kernings_ptr') != 0
                                                        or len(ctx.data('kernings') or []) != 0),
                     {'is_unknown': True})
        kernings = (OptionalBlock(child=LengthPrefixedArrayBlock(child=KerningItem(),
                                                                 length_block=IntegerBlock(length=4)),
                                  criteria=lambda ctx: ctx.data('kernings_ptr') != 0
                                                       or len(ctx.data('kernings') or []) != 0))
        padding_2 = (Padding(to=lambda ctx: ctx.data('bdata_ptr')),
                     {'is_unknown': True})
        bitmap = (EacImage(),
                  {'description': 'Font atlas bitmap data'})
        padding_3 = (Padding(to=(lambda ctx: ctx.data('block_size') + _block_size_delta(ctx),
                                 'block_size + padding_2 length (version <= 101)')),
                     {'is_unknown': True})
        remaining_bytes = (BytesBlock(length=(lambda ctx: ctx.read_bytes_remaining,
                                              'remaining bytes')),
                           {'is_unknown': True})

    def read(self, ctx: ReadContext, name: str = '', read_bytes_amount=None):
        data = super().read(ctx, name, read_bytes_amount)
        # assertions for structure consistency. This block won't work correctly if these ptr-s are not in order
        if data['kernings_ptr'] != 0:
            assert data['definitions_ptr'] <= data['kernings_ptr']
            assert data['kernings_ptr'] < data['bdata_ptr']
        else:
            assert data['definitions_ptr'] <= data['bdata_ptr']
        return data

    def serializer_class(self):
        from serializers import FfnFontSerializer
        return FfnFontSerializer
