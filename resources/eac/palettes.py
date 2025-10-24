from abc import ABC
from typing import Dict, Tuple, Any

from library.context import ReadContext
from library.read_blocks import DeclarativeCompoundBlock, BytesBlock, ArrayBlock, IntegerBlock, DataBlock
from resources.eac.fields.colors import (
    Color24BitBigEndianField,
    Color24BitDosBlock,
    Color32BitBlock,
    Color16Bit0565Block, Color16BitDosBlock,
)


class BasePalette(DeclarativeCompoundBlock, ABC):
    can_use_last_color_as_transparent = True

    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Resource with colors LUT (look-up table). EA 8-bit bitmaps have 1-byte value per pixel, '
                                 'meaning the index of color in LUT of assigned palette. Has special colors: '
                                 '255th in most cases means transparent color, 254th in car textures is replaced by '
                                 'tail light color, 250th - 253th in car textures are rendered black for unknown reason',
        }

    def new_data(self):
        return {**super().new_data(),
                'last_color_transparent': False}

    def serializer_class(self):
        from serializers import PaletteSerializer
        return PaletteSerializer

    def get_child_block(self, name: str) -> 'DataBlock':
        if name == 'last_color_transparent':
            return None
        return super().get_child_block(name)

    def get_child_block_with_data(self, unpacked_data: dict, name: str) -> Tuple['DataBlock', Any]:
        if name == 'last_color_transparent':
            return None, unpacked_data['last_color_transparent']
        return super().get_child_block_with_data(unpacked_data, name)

    def read(self, ctx: ReadContext, name: str = '', read_bytes_amount=None):
        res = super().read(ctx, name, read_bytes_amount)
        if res.get('num_colors') is not None:
            assert res['num_colors'] == res['num_colors1']
        res['last_color_transparent'] = False
        try:
            # I'm not sure how game decides whether it should draw 255th color transparent or not.
            # It appears that only qfs files in SLIDES/GSLIDES get broken if apply transparency to all bitmaps
            if self.can_use_last_color_as_transparent and len(res['colors']) >= 256 and 'SLIDES/' not in ctx.ctx_path:
                res['last_color_transparent'] = True
        except IndexError:
            pass
        return res


class PaletteReference(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (IntegerBlock(length=1, required_value=0x7C),
                       {'description': 'Resource ID'})
        unk0 = (BytesBlock(length=3),
                {'is_unknown': True})
        unk1_length = (IntegerBlock(length=4),
                       {'is_unknown': True})
        unk1 = (ArrayBlock(length=lambda ctx: 2 * ctx.data('unk1_length'),
                           child=IntegerBlock(length=4)),
                {'is_unknown': True})

    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Unknown resource. Happens after 8-bit bitmap, which does not contain embedded palette. '
                                 'Probably a reference to palette which should be used, that\'s why named so',
        }


class Palette24BitDos(BasePalette):
    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (IntegerBlock(length=1, required_value=0x22),
                       {'description': 'Resource ID'})
        unk0 = (BytesBlock(length=3),
                {'is_unknown': True})
        num_colors = (IntegerBlock(length=2),
                      {'description': 'Amount of colors',
                       'programmatic_value': lambda ctx: len(ctx.data('colors'))})
        unk1 = (BytesBlock(length=2),
                {'is_unknown': True})
        num_colors1 = (IntegerBlock(length=2),
                       {'description': 'Always equal to num_colors?',
                        'programmatic_value': lambda ctx: len(ctx.data('colors'))})
        unk2 = (BytesBlock(length=6),
                {'is_unknown': True})
        colors = (ArrayBlock(length=lambda ctx: ctx.data('num_colors'),
                             child=Color24BitDosBlock()),
                  {'description': 'Colors LUT'})


class Palette24Bit(BasePalette):
    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (IntegerBlock(length=1, required_value=0x24),
                       {'description': 'Resource ID'})
        unk0 = (BytesBlock(length=3),
                {'is_unknown': True})
        num_colors = (IntegerBlock(length=2),
                      {'description': 'Amount of colors',
                       'programmatic_value': lambda ctx: len(ctx.data('colors'))})
        unk1 = (BytesBlock(length=2),
                {'is_unknown': True})
        num_colors1 = (IntegerBlock(length=2),
                       {'description': 'Always equal to num_colors?',
                        'programmatic_value': lambda ctx: len(ctx.data('colors'))})
        unk2 = (BytesBlock(length=6),
                {'is_unknown': True})
        colors = (ArrayBlock(length=lambda ctx: ctx.data('num_colors'),
                             child=Color24BitBigEndianField()),
                  {'description': 'Colors LUT'})


class Palette16BitDos(BasePalette):
    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (IntegerBlock(length=1, required_value=0x29),
                       {'description': 'Resource ID'})
        unk0 = (BytesBlock(length=3),
                {'is_unknown': True})
        num_colors = (IntegerBlock(length=2),
                      {'description': 'Amount of colors',
                       'programmatic_value': lambda ctx: len(ctx.data('colors'))})
        unk1 = (BytesBlock(length=2),
                {'is_unknown': True})
        num_colors1 = (IntegerBlock(length=2),
                       {'description': 'Always equal to num_colors?',
                        'programmatic_value': lambda ctx: len(ctx.data('colors'))})
        unk2 = (BytesBlock(length=6),
                {'is_unknown': True})
        colors = (ArrayBlock(length=lambda ctx: ctx.data('num_colors'),
                             child=Color16BitDosBlock()),
                  {'description': 'Colors LUT'})


class Palette32Bit(BasePalette):
    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (IntegerBlock(length=1, required_value=0x2A),
                       {'description': 'Resource ID'})
        unk0 = (BytesBlock(length=3),
                {'is_unknown': True})
        num_colors = (IntegerBlock(length=2),
                      {'description': 'Amount of colors',
                       'programmatic_value': lambda ctx: len(ctx.data('colors'))})
        unk1 = (BytesBlock(length=2),
                {'is_unknown': True})
        num_colors1 = (IntegerBlock(length=2),
                       {'description': 'Always equal to num_colors?',
                        'programmatic_value': lambda ctx: len(ctx.data('colors'))})
        unk2 = (BytesBlock(length=6),
                {'is_unknown': True})
        colors = (ArrayBlock(length=lambda ctx: ctx.data('num_colors'),
                             child=Color32BitBlock()),
                  {'description': 'Colors LUT'})

    can_use_last_color_as_transparent = False


class Palette16Bit(BasePalette):
    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (IntegerBlock(length=1, required_value=0x2D),
                       {'description': 'Resource ID'})
        unk0 = (BytesBlock(length=3),
                {'is_unknown': True})
        num_colors = (IntegerBlock(length=2),
                      {'description': 'Amount of colors',
                       'programmatic_value': lambda ctx: len(ctx.data('colors'))})
        unk1 = (BytesBlock(length=2),
                {'is_unknown': True})
        num_colors1 = (IntegerBlock(length=2),
                       {'description': 'Always equal to num_colors?',
                        'programmatic_value': lambda ctx: len(ctx.data('colors'))})
        unk2 = (BytesBlock(length=6),
                {'is_unknown': True})
        colors = (ArrayBlock(length=lambda ctx: ctx.data('num_colors'),
                             child=Color16Bit0565Block()),
                  {'description': 'Colors LUT'})
