from typing import Dict

from library.context import ReadContext, WriteContext
from library.read_blocks import (
    IntegerBlock,
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
from resources.eac.bitmaps import EacImage, get_bitmap_len
from resources.eac.fields.misc import Point2D


class GlyphDefinition(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Glyph definition.<br/>'
            '- for FNT version < 200 has length 11 bytes.<br/>'
            '- for versions >= 200 and <= 309 - 12 bytes, last byte is padding.<br/>'
            '- for versions > 309 - 12th byte is num_kern.<br/>'
            '- for versions >= 321 it may be 16 bytes if "format" flag is set to 16-bytes',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        code = (IntegerBlock(length=2), {'description': 'Code of symbol'})
        width = (IntegerBlock(length=1), {'description': 'Width of symbol in font bitmap'})
        height = (IntegerBlock(length=1), {'description': 'Height of symbol in font bitmap'})
        x = (IntegerBlock(length=2), {'description': 'Position (x) of symbol in font bitmap'})
        y = (IntegerBlock(length=2), {'description': 'Position (y) of symbol in font bitmap'})
        advance = (
            IntegerBlock(length=1),
            {
                'description': 'Distance from the start of this symbol to the start of the next one in rendered text. '
                '0 in every game font with 16-byte glyphs, which keep it in `x_advance`'
            },
        )
        x_offset = (
            IntegerBlock(length=1, is_signed=True),
            {'description': 'Offset (x) for drawing the character image'},
        )
        y_offset = (
            IntegerBlock(length=1, is_signed=True),
            {'description': 'Offset (y) for drawing the character image'},
        )
        # 12-th byte
        num_kern = (
            OptionalBlock(
                child=IntegerBlock(
                    length=1,
                    is_signed=False,
                    programmatic_value=lambda ctx: sum(
                        1 for x in ctx.data('../../kernings') if x['right'] == ctx.data('code')
                    ),
                ),
                criteria=lambda ctx: ctx.data('../../version') > 309,
            ),
            {'description': 'Number of kerning pairs with this glyph as the right (second) glyph'},
        )
        pad = (
            OptionalBlock(
                child=IntegerBlock(length=1, is_signed=False),
                criteria=lambda ctx: 200 <= ctx.data('../../version') <= 309,
            ),
            {'description': 'Padding'},
        )
        # 13th - 16th bytes
        kern_index = (
            OptionalBlock(
                child=IntegerBlock(
                    length=2,
                    is_signed=False,
                    programmatic_value=lambda ctx: next(
                        (i for i, x in enumerate(ctx.data('../../kernings')) if x['right'] == ctx.data('code')), 0
                    ),
                ),
                criteria=lambda ctx: ctx.data('../../version') >= 321 and ctx.data('../../flags/format') == '16-bytes',
            ),
            {
                'description': 'Index of the first kerning pair with this glyph as the right glyph: its `num_kern` '
                'pairs follow each other in the kerning table from here. 0 if the glyph has no kerning pairs'
            },
        )
        x_advance = (
            OptionalBlock(
                child=IntegerBlock(length=2, is_signed=False),
                criteria=lambda ctx: ctx.data('../../version') >= 321 and ctx.data('../../flags/format') == '16-bytes',
            ),
            {
                'description': 'Distance from the start of this symbol to the start of the next one in rendered text, '
                'for 16-byte glyphs (`advance` is 0 in all of them in the game files)'
            },
        )

    def new_data(self, patch=None):
        data = super().new_data()
        data['width'] = 1
        data['height'] = 1
        return data


class KerningItem(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Kerning pair: horizontal adjustment of the gap between two specific glyphs',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        left = (IntegerBlock(length=2), {'description': 'Code of left glyph'})
        kerning = (
            IntegerBlock(length=1, is_signed=True),
            {'description': 'Kerning amount in pixels, added to the gap between the glyphs'},
        )
        right = (IntegerBlock(length=1), {'description': 'Code of right glyph'})


def calc_ffn_block_size(ctx):
    # modified copy from compound block's estimate_packed_size
    data = ctx.get_full_data()
    block_ctx = WriteContext(data=data, block=ctx.block, parent=None)
    res = 0
    for name, field in ctx.block.field_blocks:
        if name == 'padding_2' and ctx.data('version') <= 101:
            continue
        if name == 'bitmap' and data['bitmap']['resource_id'] == '8Bit' and data['bitmap']['embedded_palette']:
            bitmap = data['bitmap']
            res += 16 + get_bitmap_len(bitmap['resource_id'], bitmap['width'], bitmap['height'])
            continue

        # fallback default compound block estimate_packed_size logic
        usage = ctx.block.field_extras_map.get(name, {}).get('usage', 'everywhere')
        if usage != 'everywhere' and 'io' not in usage:
            continue
        res += field.estimate_packed_size(data=data.get(name), ctx=block_ctx)
    return res


class FfnFont(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'serializable_to_disc': True,
            'block_description': 'Bitmap font: a font atlas bitmap plus glyph definitions (position and size of each '
            'symbol in the atlas) and optional kerning table',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (
            UTF8Block(
                length=4,
                value_validator=Or(
                    [
                        'FNTF',
                        'FNTP',
                        'FNTS',
                        'FNTX',
                        'FNTM',
                        'FNTG',
                        'FNTA',
                        'FntF',
                        'FntP',
                        'FntS',
                        'FntX',
                        'FntM',
                        'FntG',
                        'FntA',
                    ]
                ),
            ),
            {'description': 'Resource ID'},
        )
        block_size = (
            IntegerBlock(length=4, programmatic_value=lambda ctx: calc_ffn_block_size(ctx)),
            {
                'usage': 'io,doc',
                'description': 'The length of this FFN block in bytes. Does not include the embedded palette of an '
                '8Bit bitmap (and padding to it after bitmap data); the palette of a 4Bit bitmap (NFS6) is included. '
                'For older versions (I set version <= 101,'
                ' but it can be anywhere up to < 309), "padding_2" length not included as well',
            },
        )
        version = (
            IntegerBlock(length=2, is_signed=False),
            {
                'description': 'Font format version. Defines the layout of glyph definitions (see '
                '[GlyphDefinition](#glyphdefinition))'
            },
        )
        num_glyphs = (
            IntegerBlock(length=2, programmatic_value=lambda ctx: len(ctx.data('definitions'))),
            {'usage': 'io,doc', 'description': 'Amount of symbols, defined in this font'},
        )
        flags = (
            SubByteCompoundBlock(
                length=4,
                schema=[
                    (13, 'pad', 'number', [], 'pad structure to 32 bits'),
                    (1, 'format', 'enum', ['12-bytes', '16-bytes'], ''),
                    (2, 'encoding', 'enum', ['ASCII', 'Unicode', 'Shift-JIS', 'Reserved'], ''),
                    (4, 'layoutpad', 'number', [], 'pad to save 4 other layout bits'),
                    (1, 'direction', 'enum', ['LTR', 'RTL'], ''),
                    (1, 'orientation', 'enum', ['Horizontal', 'Vertical'], ''),
                    (
                        2,
                        'baseline',
                        'enum',
                        ['Roman (english)', 'Ideographic (Kanji)', 'Hanging (Arabic)', 'Unknown'],
                        '',
                    ),
                    (4, 'drawpad', 'number', [], 'pad to save 4 other draw attribute bits'),
                    (
                        1,
                        'vram',
                        'boolean',
                        [],
                        'VRAM fonts are the default, they have extra space around the characters so that uv extraction will work under hardware.',
                    ),
                    (1, 'outline', 'boolean', [], ''),
                    (1, 'dropshadow', 'boolean', [], ''),
                    (1, 'antialiased', 'boolean', [], ''),
                ],
            ),
            {'description': 'Font flags: format of glyph definitions, encoding, layout and draw attributes'},
        )
        center = (Point2D(child=IntegerBlock(length=1, is_signed=False)), {'is_unknown': True})
        ascent = (
            IntegerBlock(length=1, is_signed=False),
            {
                'description': 'Distance from the baseline to the top of the glyphs in pixels. '
                '`ascent + descent` is the line height'
            },
        )
        descent = (
            IntegerBlock(length=1, is_signed=False),
            {'description': 'Distance from the baseline to the bottom of the glyphs in pixels'},
        )
        definitions_ptr = (
            IntegerBlock(
                length=4,
                programmatic_value=lambda ctx: ctx.block.offset_to_child_when_packed(
                    ctx.get_full_data(), 'definitions'
                ),
            ),
            {'usage': 'io,doc', 'description': 'Pointer to definitions block'},
        )
        kernings_ptr = (
            IntegerBlock(
                length=4,
                programmatic_value=lambda ctx: (
                    0
                    if len(ctx.data('kernings')) == 0
                    else ctx.block.offset_to_child_when_packed(ctx.get_full_data(), 'kernings')
                ),
            ),
            {'usage': 'io,doc', 'description': 'Pointer to kernings. 0 if there is no kernings table'},
        )
        bdata_ptr = (
            IntegerBlock(
                length=4,
                programmatic_value=lambda ctx: ctx.block.offset_to_child_when_packed(ctx.get_full_data(), 'bitmap'),
            ),
            {'usage': 'io,doc', 'description': 'Pointer to bitmap block'},
        )
        padding_0 = (Padding(to=lambda ctx: ctx.data('definitions_ptr')), {'is_unknown': True})
        definitions = (
            ArrayBlock(child=GlyphDefinition(), length=lambda ctx: ctx.data('num_glyphs')),
            {
                'description': 'Definitions of chars in this bitmap font, sorted by `code` (the writer keeps this '
                'order, stable sort by `code`)'
            },
        )
        padding_1 = (
            OptionalBlock(
                child=Padding(to=lambda ctx: ctx.data('kernings_ptr')),
                criteria=lambda ctx: ctx.data('kernings_ptr') != 0 or len(ctx.data('kernings') or []) != 0,
            ),
            {'is_unknown': True},
        )
        kernings = (
            OptionalBlock(
                child=LengthPrefixedArrayBlock(child=KerningItem(), length_block=IntegerBlock(length=4)),
                criteria=lambda ctx: ctx.data('kernings_ptr') != 0 or len(ctx.data('kernings') or []) != 0,
            ),
            {
                'description': 'Kerning pairs table. For versions > 309 (glyphs with `num_kern`) the pairs are sorted '
                'by right glyph, so the pairs of one right glyph follow each other: the writer keeps this order '
                '(stable sort by `right`)'
            },
        )
        padding_2 = (
            Padding(to=lambda ctx: ctx.data('bdata_ptr')),
            {
                'is_unknown': True,
                'description': 'Puts the bitmap at the offset the game files use: versions < 309 at a multiple of 16 '
                '(gap filled with 0xAD; NFS2 SWISS36 at a multiple of 8), newer ones so that the pixels after the '
                '16-byte bitmap header start at a multiple of 128 (gap starts with "Buy ERTS", then zeros). Recomputed '
                'on save when the glyph or kerning tables change size, keeping the alignment of the file read',
            },
        )
        bitmap = (EacImage(), {'description': 'Font atlas bitmap data'})
        remaining_bytes = (
            BytesBlock(length=(lambda ctx: ctx.read_bytes_remaining, 'remaining bytes')),
            {'is_unknown': True},
        )

    def new_data(self, patch=None):
        data = super().new_data()
        # the layout of every TNFS - NFS4 font, with a 4Bit atlas (alpha only)
        data['version'] = 100
        data['bitmap']['resource_id'] = '4Bit'
        data['bitmap']['bitmap'] = [[0]]
        return data

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        # every game font has glyphs sorted by code
        data = {**data, 'definitions': sorted(data['definitions'], key=lambda x: x['code'])}
        # glyph's num_kern and kern_index refer to a run of pairs with the same right glyph
        if data['version'] > 309 and data.get('kernings'):
            data = {**data, 'kernings': sorted(data['kernings'], key=lambda x: x['right'])}
        data['padding_2'] = self._bitmap_padding(data)
        return super().write(data, ctx, name)

    def _bitmap_padding(self, data) -> bytes:
        # padding_2 for the bitmap offset of the game files, see its description
        if data['version'] < 309:
            (align, residue) = (16, 0)
            default = b'\xad' * align
        else:
            (align, residue) = (128, 112)
            default = b'Buy ERTS' + b'\0' * align
        if data.get('bdata_ptr'):
            residue = data['bdata_ptr'] % align
        length = (residue - self.offset_to_child_when_packed(data, 'padding_2')) % align
        old = bytes(data.get('padding_2') or b'')
        return (old + default[len(old) :])[:length]

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
