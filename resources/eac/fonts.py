from typing import Dict

from library.read_blocks import IntegerBlock, UTF8Block, BytesBlock, ArrayBlock, DeclarativeCompoundBlock, \
    AutoDetectBlock
from library.read_blocks.misc.value_validators import Eq
from resources.eac.bitmaps import Bitmap4Bit, Bitmap8Bit


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
        x_advance = (IntegerBlock(length=1),
                     {'description': 'Gap between this symbol and next one in rendered text'})
        x_offset = (IntegerBlock(length=1, is_signed=True),
                    {'description': 'Offset (x) for drawing the character image'})
        y_offset = (IntegerBlock(length=1, is_signed=True),
                    {'description': 'Offset (y) for drawing the character image'})


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
        unk0 = (BytesBlock(length=2),
                {'is_unknown': True})
        num_glyphs = (IntegerBlock(length=2,
                                   programmatic_value=lambda ctx: len(ctx.data('definitions'))),
                      {'description': 'Amount of symbols, defined in this font'})
        unk1 = (BytesBlock(length=6),
                {'is_unknown': True})
        font_size = (IntegerBlock(length=1),
                     {'description': 'Font size ?'})
        unk2 = (IntegerBlock(length=1),
                {'is_unknown': True})
        line_height = (IntegerBlock(length=1),
                       {'description': 'Line height ?'})
        unk3 = (BytesBlock(length=7),
                {'is_unknown': True})
        bdata_ptr = (IntegerBlock(length=4,
                                  programmatic_value=lambda ctx: ctx.block.offset_to_child_when_packed(
                                      ctx.get_full_data(),
                                      'bitmap')),
                     {'description': 'Pointer to bitmap block'})
        definitions = (ArrayBlock(child=GlyphDefinition(), length=lambda ctx: ctx.data('num_glyphs')),
                       {'description': 'Definitions of chars in this bitmap font'})
        skip_bytes = (BytesBlock(length=(lambda ctx: ctx.data('bdata_ptr') - ctx.buffer.tell(),
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
