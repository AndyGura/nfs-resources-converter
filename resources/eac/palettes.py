from abc import ABC
from io import BufferedReader, BytesIO
from typing import Dict

from library2.context import ReadContext
from library2.read_blocks import DeclarativeCompoundBlock, BytesBlock, ArrayBlock, IntegerBlock
from resources.eac.fields.colors import (
    Color24BitBigEndianField,
    Color24BitDosBlock,
    Color32BitBlock,
    Color16Bit0565Block,
)

transparency_colors = [
    # default
    0xFF_00_FF_FF,
    0x00_FF_00_FF,
    0x00_00_FF_FF,
    # green-ish
    0x00_EA_1C_FF,  # TNFS lost vegas map props
    0x00_EB_1C_FF,  # TNFS lost vegas map props
    # 0x00_FB_00_FF,  # NFS2 GAMEDATA/TRACKS/SE/TR050M, not working, there is Bitmap 0565 without alpha
    0x04_FF_00_FF,
    0x0C_FF_00_FF,
    0x24_ff_10_FF,  # TNFS TRAFFC.CFM
    0x28_FF_28_FF,
    0x28_FF_2C_FF,
    # blue
    0x00_00_FC_FF,  # TNFS Porsche 911 CFM
    # light blue
    0x00_FF_FF_FF,
    0x1a_ff_ff_ff,  # NFS2SE TRACKS/PC/TR000M.QFS
    0x48_ff_ff_FF,  # NFS2SE TRACKS/PC/TR020M.QFS
    # purple
    0xCE_1C_C6_FF,  # some TNFS map props
    0xF2_00_FF_FF,
    0xFF_00_F7_FF,  # TNFS AL2 map props
    0xFF_00_F6_FF,  # TNFS NTRACKFM/AL3_T01.FAM map props
    0xFF_31_59_FF,  # TNFS ETRACKFM/CL3_001.FAM road sign
    # gray
    0x28_28_28_FF,  # car wheels
    0xFF_FF_FF_FF,  # map props
    0x00_00_00_FF,  # some menu items: SHOW/DIABLO.QFS
]


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

    def read(self, buffer: [BufferedReader, BytesIO], ctx: ReadContext = None, name: str = '', read_bytes_amount=None):
        res = super().read(buffer, ctx, name)
        res['last_color_transparent'] = False
        try:
            if self.can_use_last_color_as_transparent and res['colors'][255] in transparency_colors:
                res['last_color_transparent'] = True
        except IndexError:
            pass
        return res


# TODO 41 (0x29) 16 bit dos palette


class PaletteReference(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (IntegerBlock(length=1, required_value=0x7C),
                       {'description': 'Resource ID'})
        unknowns = (BytesBlock(length=7),
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
        unknowns = (BytesBlock(length=15),
                    {'is_unknown': True})
        colors = (ArrayBlock(length=256, child=Color24BitDosBlock()),
                  {'description': 'Colors LUT'})


class Palette24Bit(BasePalette):
    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (IntegerBlock(length=1, required_value=0x24),
                       {'description': 'Resource ID'})
        unknowns = (BytesBlock(length=15),
                    {'is_unknown': True})
        colors = (ArrayBlock(length=256, child=Color24BitBigEndianField()),
                  {'description': 'Colors LUT'})


class Palette32Bit(BasePalette):
    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (IntegerBlock(length=1, required_value=0x2A),
                       {'description': 'Resource ID'})
        unknowns = (BytesBlock(length=15),
                    {'is_unknown': True})
        colors = (ArrayBlock(length=256, child=Color32BitBlock()),
                  {'description': 'Colors LUT'})

    can_use_last_color_as_transparent = False


class Palette16Bit(BasePalette):
    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (IntegerBlock(length=1, required_value=0x2D),
                       {'description': 'Resource ID'})
        unknowns = (BytesBlock(length=15),
                    {'is_unknown': True})
        colors = (ArrayBlock(length=256, child=Color16Bit0565Block()),
                  {'description': 'Colors LUT'})
