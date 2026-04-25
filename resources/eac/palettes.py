from typing import Dict, Tuple, Any

from library.context import ReadContext
from library.read_blocks import (DeclarativeCompoundBlock,
                                 BytesBlock,
                                 ArrayBlock,
                                 IntegerBlock,
                                 DataBlock,
                                 EnumByteBlock,
                                 EnumLookupDelegateBlock,
                                 )
from library.read_blocks.misc.value_validators import Eq
from resources.eac.fields.colors import (Color24BitBigEndianField,
                                         Color24BitDosBlock,
                                         Color32BitBlock,
                                         Color16Bit0565Block,
                                         Color16BitDosBlock,
                                         )


class EacPalette(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (EnumByteBlock(enum_names=[(0x22, '24BitDos color format palette'),
                                                 (0x24, '16Bit color format palette'),
                                                 (0x29, '16BitUnk color format palette'),
                                                 (0x2A, '32Bit color format palette'),
                                                 # TODO colors 15-0 ? found here https://bitbucket.org/fifam/otools/src/master/OTools/Fsh/Fsh.h
                                                 (0x2D, '16Bit_0565 color format palette')]),
                       {'description': 'Resource ID'})
        unk0 = (BytesBlock(length=3),
                {'is_unknown': True})
        num_colors = (IntegerBlock(length=2,
                                   programmatic_value=lambda ctx: len(ctx.data('colors'))),
                      {'description': 'Amount of colors'})
        unk1 = (BytesBlock(length=2),
                {'is_unknown': True})
        num_colors1 = (IntegerBlock(length=2,
                                    programmatic_value=lambda ctx: len(ctx.data('colors'))),
                       {'description': 'Always equal to num_colors?'})
        unk2 = (BytesBlock(length=6),
                {'is_unknown': True})
        colors = (EnumLookupDelegateBlock(enum_field='resource_id',
                                          blocks=[
                                              ArrayBlock(length=lambda ctx: ctx.data('num_colors'),
                                                         child=Color24BitDosBlock()),
                                              ArrayBlock(length=lambda ctx: ctx.data('num_colors'),
                                                         child=Color24BitBigEndianField()),
                                              ArrayBlock(length=lambda ctx: ctx.data('num_colors'),
                                                         child=Color16BitDosBlock()),
                                              ArrayBlock(length=lambda ctx: ctx.data('num_colors'),
                                                         child=Color32BitBlock()),
                                              ArrayBlock(length=lambda ctx: ctx.data('num_colors'),
                                                         child=Color16Bit0565Block())
                                          ]),
                  {'description': 'Colors LUT. Color model is selected according to `resource_id` field. '
                                  'Color models are described [here](eac_colors.md)'})

    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Resource with colors LUT (look-up table). EA 8-bit bitmaps have 1-byte value per pixel, '
                                 'meaning the index of color in LUT of assigned palette. Has special colors: '
                                 '255th in most cases means transparent color, 254th in car textures is replaced by '
                                 'tail light color, 250th - 253th in car textures are rendered black: thy are reserved '
                                 'for cop car siren',
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
            if not res['resource_id'].startswith('32Bit') and len(res['colors']['data']) >= 256 and 'SLIDES/' not in ctx.ctx_path:
                res['last_color_transparent'] = True
        except IndexError:
            pass
        return res
