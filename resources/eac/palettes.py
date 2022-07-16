from abc import ABC

from library.read_blocks.array_field import ArrayBlock
from library.read_blocks.atomic import IntegerField
from library.read_blocks.compound_block import CompoundBlock
from resources.eac.fields.colors import (
    Color24BitBigEndianField,
    Color24BitDosField,
    Color32BitField,
    Color16Bit0565Field,
)


# TODO probably this flag is somewhere in image resource, need to find it
def is_last_color_transparent(color):
    return color in [
        # green-ish
        0x00_EA_1C_FF,  # TNFS lost vegas map props
        0x00_EB_1C_FF,  # TNFS lost vegas map props
        # 0x00_FB_00_FF,  # NFS2 GAMEDATA/TRACKS/SE/TR050M TODO not working, there is Bitmap 0565 without alpha
        0x00_FF_00_FF,
        0x04_FF_00_FF,
        0x0C_FF_00_FF,
        0x24_ff_10_FF,  # TNFS TRAFFC.CFM
        0x28_FF_28_FF,
        0x28_FF_2C_FF,
        # blue
        0x00_00_FF_FF,
        0x00_00_FC_FF,  # TNFS Porsche 911 CFM
        # light blue
        0x00_FF_FF_FF,
        0x1a_ff_ff_ff,  # NFS2SE TRACKS/PC/TR000M.QFS
        0x48_ff_ff_FF,  # NFS2SE TRACKS/PC/TR020M.QFS
        # purple
        0xCE_1C_C6_FF,  # some TNFS map props
        0xF2_00_FF_FF,
        0xFF_00_F7_FF,  # TNFS AL2 map props
        0xFF_00_FF_FF,
        0xFF_00_F6_FF,  # TNFS NTRACKFM/AL3_T01.FAM map props
        0xFF_31_59_FF,  # TNFS ETRACKFM/CL3_001.FAM road sign
        # gray
        0x28_28_28_FF,  # car wheels
        0xFF_FF_FF_FF,  # map props
        0x00_00_00_FF,  # some menu items: SHOW/DIABLO.QFS
    ]


class BasePalette(CompoundBlock, ABC):
    can_use_last_color_as_transparent = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.block_description = 'Resource with colors LUT (look-up table). EA 8-bit bitmaps have 1-byte value per pixel, ' \
                                 'meaning the index of color in LUT of assigned palette'

    def from_raw_value(self, raw: dict):
        res = super().from_raw_value(raw)
        try:
            if self.can_use_last_color_as_transparent and is_last_color_transparent(res.colors[255]):
                res.colors[255] = 0
        except IndexError:
            pass
        return res


# TODO 41 (0x29) 16 bit dos palette


class PaletteReference(CompoundBlock):
    class Fields(CompoundBlock.Fields):
        resource_id = IntegerField(static_size=1, is_signed=False, required_value=0x7C, description='Resource ID')
        unknowns = ArrayBlock(length=7, child=IntegerField(static_size=1), is_unknown=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.block_description = 'Unknown resource. Happens after 8-bit bitmap, which does not contain embedded palette. ' \
                                 'Probably a reference to palette which should be used, that\'s why named so'


class Palette24BitDos(BasePalette):
    class Fields(CompoundBlock.Fields):
        resource_id = IntegerField(static_size=1, is_signed=False, required_value=0x22, description='Resource ID')
        unknowns = ArrayBlock(length=15, child=IntegerField(static_size=1), is_unknown=True)
        colors = ArrayBlock(length=256, child=Color24BitDosField(), length_strategy="read_available",
                            description='Colors LUT')


class Palette24Bit(BasePalette):
    class Fields(CompoundBlock.Fields):
        resource_id = IntegerField(static_size=1, is_signed=False, required_value=0x24, description='Resource ID')
        unknowns = ArrayBlock(length=15, child=IntegerField(static_size=1), is_unknown=True)
        colors = ArrayBlock(length=256, child=Color24BitBigEndianField(), length_strategy="read_available",
                            description='Colors LUT')


class Palette32Bit(BasePalette):
    class Fields(CompoundBlock.Fields):
        resource_id = IntegerField(static_size=1, is_signed=False, required_value=0x2A, description='Resource ID')
        unknowns = ArrayBlock(length=15, child=IntegerField(static_size=1), is_unknown=True)
        colors = ArrayBlock(length=256, child=Color32BitField(), length_strategy="read_available",
                            description='Colors LUT')

    can_use_last_color_as_transparent = False


class Palette16Bit(BasePalette):
    class Fields(CompoundBlock.Fields):
        resource_id = IntegerField(static_size=1, is_signed=False, required_value=0x2D, description='Resource ID')
        unknowns = ArrayBlock(length=15, child=IntegerField(static_size=1), is_unknown=True)
        colors = ArrayBlock(length=256, child=Color16Bit0565Field(), length_strategy="read_available",
                            description='Colors LUT')
