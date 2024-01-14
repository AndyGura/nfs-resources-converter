from typing import Dict

from library2.read_blocks import CompoundBlock, IntegerBlock, UTF8Block, BytesBlock, ArrayBlock
from resources.eac.bitmaps import Bitmap4Bit


class SymbolDefinitionRecord(CompoundBlock):
    class Fields(CompoundBlock.Fields):
        code = (IntegerBlock(length=2),
                {'description': 'Code of symbol'})
        glyph_width = (IntegerBlock(length=1),
                       {'description': 'Width of symbol in font bitmap'})
        glyph_height = (IntegerBlock(length=1),
                        {'description': 'Height of symbol in font bitmap'})
        glyph_x = (IntegerBlock(length=2),
                   {'description': 'Position (x) of symbol in font bitmap'})
        glyph_y = (IntegerBlock(length=2),
                   {'description': 'Position (y) of symbol in font bitmap'})
        x_advance = (IntegerBlock(length=1),
                     {'description': 'Gap between this symbol and next one in rendered text'})
        x_offset = (IntegerBlock(length=1, is_signed=True),
                    {'description': 'Offset (x) for drawing the character image'})
        y_offset = (IntegerBlock(length=1, is_signed=True),
                    {'description': 'Offset (y) for drawing the character image'})


class FfnFont(CompoundBlock):

    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'serializable_to_disc': True,
        }

    class Fields(CompoundBlock.Fields):
        resource_id = (UTF8Block(length=4, required_value='FNTF'),
                       {'description': 'Resource ID'})
        block_size = (IntegerBlock(length=4),
                      {'description': 'This FFN block size in bytes',
                       'programmatic_value': lambda ctx: ctx.block.estimate_packed_size(ctx.get_full_data())})
        unk0 = (IntegerBlock(length=1, required_value=100),
                {'is_unknown': True})
        unk1 = (IntegerBlock(length=1, required_value=0),
                {'is_unknown': True})
        symbols_amount = (IntegerBlock(length=2),
                          {'description': 'Amount of symbols, defined in this font',
                           'programmatic_value': lambda ctx: len(ctx.data('definitions'))})
        unk2 = (BytesBlock(length=6),
                {'is_unknown': True})
        font_size = (IntegerBlock(length=1),
                     {'description': 'Font size ?'})
        unk3 = (IntegerBlock(length=1, required_value=0),
                {'is_unknown': True})
        line_height = (IntegerBlock(length=1),
                       {'description': 'Line height ?'})
        unk4 = (BytesBlock(length=7, required_value=b'\0' * 7),
                {'is_unknown': True})
        bitmap_data_pointer = (IntegerBlock(length=2),
                               {'description': 'Pointer to bitmap block',
                                'programmatic_value': lambda ctx: ctx.block.offset_to_child_when_packed(
                                    ctx.get_full_data(), 'bitmap')})
        unk5 = (IntegerBlock(length=1, required_value=0),
                {'is_unknown': True})
        unk6 = (IntegerBlock(length=1, required_value=0),
                {'is_unknown': True})
        definitions = (ArrayBlock(child=SymbolDefinitionRecord(), length=(lambda ctx: ctx.data('symbols_amount'),
                                                                          'symbols_amount')),
                       {'description': 'Definitions of chars in this bitmap font'})
        skip_bytes = (BytesBlock(length=(lambda ctx: ctx.data('bitmap_data_pointer') - ctx.buffer.tell(),
                                         'up to offset bitmap_data_pointer')),
                      {'description': '4-bytes AD AD AD AD (optional, happens in nfs2 SWISS36)'})
        bitmap = (Bitmap4Bit(),
                  {'description': 'Font atlas bitmap data',
                   'custom_offset': 'bitmap_data_pointer'})
