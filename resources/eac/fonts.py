from library.read_blocks.array import ArrayBlock
from library.read_blocks.atomic import IntegerBlock, Utf8Block, AtomicDataBlock
from library.read_blocks.compound import CompoundBlock
from resources.eac.bitmaps import Bitmap4Bit


class SymbolDefinitionRecord(CompoundBlock):
    class Fields(CompoundBlock.Fields):
        code = IntegerBlock(static_size=2, description='Code of symbol')
        glyph_width = IntegerBlock(static_size=1, description='Width of symbol in font bitmap')
        glyph_height = IntegerBlock(static_size=1, description='Height of symbol in font bitmap')
        glyph_x = IntegerBlock(static_size=2, description='Position (x) of symbol in font bitmap')
        glyph_y = IntegerBlock(static_size=2, description='Position (Y) of symbol in font bitmap')
        x_advance = IntegerBlock(static_size=1, description='Gap between this symbol and next one in rendered text')
        x_offset = IntegerBlock(static_size=1, is_signed=True, description='Offset (x) for drawing the character image')
        y_offset = IntegerBlock(static_size=1, is_signed=True, description='Offset (y) for drawing the character image')


class FfnFont(CompoundBlock):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_serializable_to_disk = True

    class Fields(CompoundBlock.Fields):
        resource_id = Utf8Block(required_value='FNTF', length=4, description='Resource ID')
        file_size = IntegerBlock(static_size=4, description='This file size in bytes')
        unk0 = IntegerBlock(static_size=1, required_value=100)
        unk1 = IntegerBlock(static_size=1, required_value=0)
        symbols_amount = IntegerBlock(static_size=2, description='Amount of symbols, defined in this font')
        unk2 = AtomicDataBlock(static_size=6)
        font_size = IntegerBlock(static_size=1, description='Font size ?')
        unk3 = IntegerBlock(static_size=1, required_value=0)
        line_height = IntegerBlock(static_size=1, description='Line height ?')
        unk4 = AtomicDataBlock(static_size=7, required_value=b'\0' * 7)
        bitmap_data_pointer = IntegerBlock(static_size=2, description='Pointer to bitmap block')
        unk5 = IntegerBlock(static_size=1, required_value=0)
        unk6 = IntegerBlock(static_size=1, required_value=0)
        definitions = ArrayBlock(child=SymbolDefinitionRecord(), length_label='symbols_amount',
                                 description='Definitions of chars in this bitmap font')
        skip_bytes = ArrayBlock(length_label='up to offset bitmap_data_pointer',
                                child=IntegerBlock(static_size=1, required_value=0xAD),
                                description='4-bytes AD AD AD AD (optional, happens in nfs2 SWISS36)')
        bitmap = Bitmap4Bit(description='Font atlas bitmap data')

        unknown_fields = ['unk0', 'unk1', 'unk2', 'unk3', 'unk4', 'unk5', 'unk6']

    def _after_symbols_amount_read(self, data, state, **kwargs):
        if not state.get('definitions'):
            state['definitions'] = {}
        state['definitions']['length'] = data['symbols_amount'].value

    def _after_definitions_read(self, data, state, buffer, **kwargs):
        if not state.get('skip_bytes'):
            state['skip_bytes'] = {}
        state['skip_bytes']['length'] = data['bitmap_data_pointer'].value - buffer.tell()
