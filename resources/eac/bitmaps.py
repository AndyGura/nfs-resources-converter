from copy import deepcopy
from functools import lru_cache
from io import BytesIO, SEEK_CUR
from typing import Tuple, Any, Dict

import numpy as np
from math import ceil

from library.context import ReadContext, WriteContext
from library.read_blocks import (
    DataBlock,
    DeclarativeCompoundBlock,
    IntegerBlock,
    SubByteArrayBlock,
    BytesBlock,
    ArrayBlock,
    EnumByteBlock,
    EnumLookupDelegateBlock,
    TrailingOptionalBlock,
    LengthPrefixedArrayBlock,
    Padding,
)
from library.read_blocks.misc.value_validators import Eq
from library.read_blocks.strings import LengthPrefixedUtf8Block
from library.utils import transform_bitness, extract_number, is_power_of_two
from library.utils.dxt import decode_dxt, dxt_byte_len, encode_dxt
from library.utils.id import join_id
from resources.eac.fields.misc import Point2D


@lru_cache(maxsize=256)
def transform_color_bitness(color, alpha_bitness, red_bitness, green_bitness, blue_bitness):
    alpha = (
        transform_bitness(
            extract_number(color, alpha_bitness, red_bitness + green_bitness + blue_bitness), alpha_bitness
        )
        if alpha_bitness
        else 0xFF
    )
    red = transform_bitness(extract_number(color, red_bitness, green_bitness + blue_bitness), red_bitness)
    green = transform_bitness(extract_number(color, green_bitness, blue_bitness), green_bitness)
    blue = transform_bitness(extract_number(color, blue_bitness), blue_bitness)
    return int(red << 24 | green << 16 | blue << 8 | alpha)


@lru_cache(maxsize=256)
def revert_color_bitness(color, alpha_bitness, red_bitness, green_bitness, blue_bitness):
    alpha = (color & 0xFF) >> (8 - alpha_bitness)
    red = (color & 0xFF000000) >> (32 - red_bitness)
    green = (color & 0xFF0000) >> (24 - green_bitness)
    blue = (color & 0xFF00) >> (16 - blue_bitness)
    return (
        alpha << (red_bitness + green_bitness + blue_bitness)
        | red << (green_bitness + blue_bitness)
        | green << blue_bitness
        | blue
    )


def get_bitmap_len(resource_id, width, height):
    if resource_id[:3] == 'DXT':
        return dxt_byte_len(resource_id[:4], width, height)
    elif resource_id[:2] == '16':
        return 2 * width * height
    elif resource_id[:2] == '24':
        return 3 * width * height
    elif resource_id[:2] == '32':
        return 4 * width * height
    elif resource_id[:1] == '4':
        return ceil(width / 2) * height
    elif resource_id[:1] == '8':
        return width * height
    else:
        return 0


def mipmap_level_dims(width: int, height: int):
    """Yield (level_width, level_height) for each mipmap level, from w/2 x h/2 down to 1x1."""
    while width > 1 or height > 1:
        width = max(1, width // 2)
        height = max(1, height // 2)
        yield width, height


MIPMAP_LEVEL_ALIGNMENT = 16


def mipmap_level_byte_len(resource_id, width: int, height: int) -> int:
    """Bytes of one mipmap level in a file: its pixels, padded with zeros to 16 bytes (NFS5)"""
    length = get_bitmap_len(resource_id, width, height)
    return -(-length // MIPMAP_LEVEL_ALIGNMENT) * MIPMAP_LEVEL_ALIGNMENT


def mipmaps_byte_len(resource_id, width: int, height: int) -> int:
    """Return the total number of bytes in all mipmap levels excluding the base level, with level padding."""
    return sum(mipmap_level_byte_len(resource_id, w, h) for (w, h) in mipmap_level_dims(width, height))


def mipmap_count(position_y: int) -> int:
    """Amount of mipmap levels, stored in the 4 high bits of `position.y`"""
    return position_y >> 12


PALETTE_IDS = [0x22, 0x24, 0x29, 0x2A, 0x2D]
HOT_SPOTS_ID = 0x7C
TEXT_ID = 0x6F
# blocks of an image's chain (see `EacImage.next_offset`) parsed into named fields, in the order they come in files
CHAINED_FIELDS = ['embedded_palette', 'hot_spots', 'text']


def _chain_next_pos(ctx):
    """Local offset of the next block of the image's chain after the blocks read so far, None when the chain ended"""
    pos = ctx.data('next_offset')
    if pos <= 0:
        return None
    for name in CHAINED_FIELDS:
        block = ctx.data(name)
        if block is not None:
            if block['next_offset'] == 0:
                return None
            pos += block['next_offset']
    return pos


def _peek_id(ctx, pos):
    """id byte of the block at local offset `pos`, None when it is not inside the read item"""
    if pos is None or pos < ctx.local_buffer_pos or ctx.read_bytes_remaining is None:
        return None
    if pos - ctx.local_buffer_pos >= ctx.read_bytes_remaining:
        return None
    current = ctx.buffer.tell()
    ctx.buffer.seek(pos - ctx.local_buffer_pos, SEEK_CUR)
    try:
        return ctx.buffer.read(1)[0]
    finally:
        ctx.buffer.seek(current)


def chained_block_criteria(ids, min_size):
    """Criteria of a chained block: the chain continues right here, with a block of one of `ids`"""

    def criteria(ctx, **kwargs):
        if not isinstance(ctx, ReadContext):
            return False
        pos = _chain_next_pos(ctx)
        return (
            pos == ctx.local_buffer_pos
            and ctx.read_bytes_remaining is not None
            and ctx.read_bytes_remaining >= min_size
            and _peek_id(ctx, pos) in ids
        )

    return criteria


def chain_padding_criteria(ctx, **kwargs):
    """Bytes between the block just read and the next block of the chain, when that one is parsed into a field"""
    if not isinstance(ctx, ReadContext):
        return False
    pos = _chain_next_pos(ctx)
    return pos is not None and pos > ctx.local_buffer_pos and _peek_id(ctx, pos) in [HOT_SPOTS_ID, TEXT_ID]


def chain_padding_length(ctx):
    return _chain_next_pos(ctx) - ctx.local_buffer_pos


def image_padding_criteria(ctx, **kwargs):
    if not isinstance(ctx, ReadContext) or ctx.read_bytes_remaining is None:
        return False
    gap = ctx.data('next_offset') - ctx.local_buffer_pos
    if gap == 0:
        # a block kept as raw bytes right after the pixels (NFS6 0x70): an empty padding marks the link, so that the
        # offset follows the pixels on save
        return _peek_id(ctx, ctx.local_buffer_pos) not in [None, *PALETTE_IDS, HOT_SPOTS_ID, TEXT_ID]
    return 0 < gap <= ctx.read_bytes_remaining


def unlinked_palette_criteria(ctx, **kwargs):
    if not isinstance(ctx, ReadContext):
        return False
    if ctx.data('resource_id') != '8Bit' or ctx.data('embedded_palette') is None or _chain_next_pos(ctx) is not None:
        return False
    if ctx.read_bytes_remaining is None or ctx.read_bytes_remaining < 16:
        return False
    return _peek_id(ctx, ctx.local_buffer_pos) in PALETTE_IDS


def mipmaps_presence_criteria(ctx, **kwargs):
    if not isinstance(ctx, ReadContext) or ctx.read_bytes_remaining is None:
        return False
    width, height = ctx.data('width'), ctx.data('height')
    if not is_power_of_two(width) or not is_power_of_two(height):
        return False
    levels = len(list(mipmap_level_dims(width, height)))
    # every file with mipmaps (NFS5) has the full chain of levels
    if levels == 0 or mipmap_count(ctx.data('position/y')) != levels:
        return False
    mipmaps_len = mipmaps_byte_len(ctx.data('resource_id'), width, height)
    if ctx.read_bytes_remaining < mipmaps_len:
        return False
    next_offset = ctx.data('next_offset')
    if next_offset > 0:
        # the image data, mipmaps included, ends where the first attached block starts (up to alignment)
        return 0 <= next_offset - ctx.local_buffer_pos - mipmaps_len < 16
    return True


def _stored_next_offset(ctx):
    # `EacImage.write` sets the offsets of the chain (`_link_chained_blocks`): programmatic for the GUI to show them
    # read-only, written as they are
    return ctx.data('next_offset')


NEXT_OFFSET_DESCRIPTION = (
    'Offset from the start of this block to the next block attached to the same bitmap (0 when this is the last '
    'one). Recomputed on save when a block parsed into a field follows'
)


class ShpiHotSpots(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (IntegerBlock(length=1, value_validator=Eq(0x7C)), {'description': 'Resource ID'})
        next_offset = (
            IntegerBlock(length=3, programmatic_value=_stored_next_offset),
            {'description': NEXT_OFFSET_DESCRIPTION},
        )
        points = (
            LengthPrefixedArrayBlock(
                length_block=(IntegerBlock(length=4)), child=Point2D(child=IntegerBlock(length=4, is_signed=True))
            ),
            {
                'description': 'Points in screen pixels, relative to the bitmap: the screen point is `position` + '
                '`pivot` + point, so `pivot` + point is the pixel of the bitmap. TNFS reads the low byte of the amount '
                'only'
            },
        )

    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'A list of hot spots: points of interest of the bitmap it is attached to (after the '
            'bitmap and its embedded palette), the index of a point gives its meaning. Many bitmaps of menus, track '
            '(FAM) and car (CFM) textures have an empty list, others in the same files have none, and 1x1 '
            'placeholder bitmaps of dashboards have copies of the list of another bitmap. TNFS reads it in the dashboard loader only '
            '(DOS `tnfs_dash_000522be`, Win95 SE FUN_0041f9a0, the demo `tnfs_dashboard_load`; PSX and 3DO do not '
            'read FSH dashboards), from four bitmaps of `SIMDATA/DASH/*DH.FSH` / `*DL.FSH`:<br/>'
            '- `dash`: 10 points. 0, 1 = top left and bottom right corners of the rear-view mirror; 2 = radar '
            'detector power light; 3..7 = the 5 radar detector level lights; 8, 9 = the loader turns them into '
            'offsets from 2 and 3, nothing reads them<br/>'
            '- `tach`: tachometer needle tip at 0, 1024, 2048... RPM (the needle is interpolated between them), '
            'the last point is the needle centre<br/>'
            '- `sped`: speedometer needle tip at 0, 10, 20... mph (0, 20, 40... km/h in the German version), the '
            'last point is the needle centre. The cars with a digital speedometer draw digits instead<br/>'
            '- `gate`: gear lever knob position for every gear: 0 = reverse, 1 = neutral, then gears from 1st: 7 or 8 '
            'points. The game reads 9 points (a 9th, where present, is at the corner of the bitmap)<br/>'
            'The game walks the attached blocks until it finds 0x7C, so it hangs when one of these bitmaps has '
            'no hot spots',
        }


class ShpiText(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'An entry, which sometimes can be seen in the SHPI archive block after bitmap, '
            'contains some text. The purpose is unclear',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (IntegerBlock(length=1, value_validator=Eq(0x6F)), {'description': 'Resource ID'})
        next_offset = (
            IntegerBlock(length=3, programmatic_value=_stored_next_offset),
            {'description': NEXT_OFFSET_DESCRIPTION},
        )
        text = (LengthPrefixedUtf8Block(length_block=IntegerBlock(length=4)), {'description': 'Text contents'})

    def serializer_class(self):
        from serializers import ShpiTextSerializer

        return ShpiTextSerializer


class EacPalette(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (
            EnumByteBlock(
                enum_names=[
                    (0x22, '24BitDos color format palette'),
                    (0x24, '24Bit color format palette'),
                    (0x29, '16Bit_0565 color format palette'),
                    (0x2A, '32Bit color format palette'),
                    # TODO colors 15-0 ? found here https://bitbucket.org/fifam/otools/src/master/OTools/Fsh/Fsh.h
                    (0x2D, '16Bit_1555 color format palette'),
                ]
            ),
            {'description': 'Resource ID'},
        )
        next_offset = (
            IntegerBlock(length=3, programmatic_value=_stored_next_offset),
            {
                'description': 'When attached to a bitmap: '
                + NEXT_OFFSET_DESCRIPTION[0].lower()
                + NEXT_OFFSET_DESCRIPTION[1:]
                + '. 0 in palette items (`!pal`)'
            },
        )
        num_colors = (
            IntegerBlock(length=2, programmatic_value=lambda ctx: len(ctx.data('colors/data'))),
            {'usage': 'io,doc', 'description': 'Amount of colors'},
        )
        unk1 = (BytesBlock(length=2), {'is_unknown': True})
        num_colors1 = (
            IntegerBlock(length=2, programmatic_value=lambda ctx: len(ctx.data('colors/data'))),
            {'usage': 'io,doc', 'description': 'Equals to num_colors, except for some CRP structures in NFS5'},
        )
        unk2 = (BytesBlock(length=6), {'is_unknown': True})
        colors = (
            EnumLookupDelegateBlock(
                enum_field='resource_id',
                blocks=[
                    ArrayBlock(
                        length=lambda ctx: ctx.data('num_colors'), child=IntegerBlock(length=3, byte_order='big')
                    ),
                    ArrayBlock(
                        length=lambda ctx: ctx.data('num_colors'), child=IntegerBlock(length=3, byte_order='big')
                    ),
                    ArrayBlock(length=lambda ctx: ctx.data('num_colors'), child=IntegerBlock(length=2)),
                    ArrayBlock(length=lambda ctx: ctx.data('num_colors'), child=IntegerBlock(length=4)),
                    ArrayBlock(length=lambda ctx: ctx.data('num_colors'), child=IntegerBlock(length=2)),
                ],
            ),
            {
                'description': 'Colors LUT. Color model is selected according to `resource_id` field. '
                'Color models are described [here](eac_colors.md)'
            },
        )

    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'custom_actions': [
                {
                    'method': 'invert_colors',
                    'title': 'Invert colors',
                    'description': 'Inverts all colors',
                    'is_pure': False,
                    'args': [],
                },
                {
                    'method': 'convert_format',
                    'title': 'Convert color format',
                    'description': 'Converts color format',
                    'is_pure': False,
                    'args': [
                        {
                            'id': 'color_mode',
                            'title': 'Color mode',
                            'type': 'enum_string',
                            'choices': [
                                '24BitDos color format palette',
                                '24Bit color format palette',
                                '16Bit_0565 color format palette',
                                '32Bit color format palette',
                                '16Bit_1555 color format palette',
                            ],
                        }
                    ],
                },
            ],
            'block_description': 'Resource with colors LUT (look-up table). EA 8-bit bitmaps have 1-byte value per pixel, '
            'meaning the index of color in LUT of assigned palette. Has special colors: '
            '255th in most cases means transparent color, 254th in TNFS car textures is replaced by '
            'tail light color, 250th - 253th are the cop car light bar (TNFS maps them to the VGA palette entries '
            '0xFA - 0xFD: red, dark red, blue, dark blue, swapped every 16 clock ticks during a police chase, Win95 SE '
            '`gfx_draw_car_model` 0x458d4c) and are rendered black in other cars. The converter writes these colors '
            'to `car_colors.json` next to the PNGs.<br/>'
            'TNFS car models (CFM) have a second palette `!xxx` next to `!PAL` in the high-poly textures SHPI (TRAFFC '
            "in both): the car's slice of the shared 256-color VGA palette in 8-bit modes (Win95 SE "
            '`gfx_car_palettes_setup` 0x4572e0). Its first 23 colors (8 for traffic, 24 for the player in a single '
            "race / tournament) go to the car's palette entries (player 0x30, opponent 0x48, traffic 0x60 + 8 * "
            'slot), then the textures are remapped from `!PAL` to the nearest colors of the VGA palette. `!PAL` is '
            'the palette of the textures, `!xxx` is never used to draw them. Cops get none, and the `M*.CFM` models '
            '(opponents of a single race / tournament, which share `CARFAMS/CARPAL.FSH` instead) have junk there. '
            'Many `!xxx` have the 8-bit bitmap id 0x7B (256x1 or 256x3) instead of a palette id. The converter '
            'writes its used colors to `car_colors.json` (`palette_slice`) instead of a file of its own',
        }

    def new_data(self, patch=None):
        return {**super().new_data(), 'last_color_transparent': False}

    def serializer_class(self):
        from serializers import PaletteSerializer

        return PaletteSerializer

    def get_child_block(self, name: str) -> 'DataBlock':
        if name == 'last_color_transparent':
            return None
        return super().get_child_block(name)

    def _colors_native_to_internal(self, resource_id, colors):
        if resource_id == '24BitDos color format palette':
            return [(x & 0x3F3F3F) << 10 | 255 for x in colors]
        elif resource_id == '24Bit color format palette':
            return [x << 8 | 0xFF for x in colors]
        elif resource_id == '16Bit_0565 color format palette':
            return [transform_color_bitness(x, 0, 5, 6, 5) for x in colors]
        elif resource_id == '32Bit color format palette':
            # ARGB => RGBA
            return [(x & 0x00_FF_FF_FF) << 8 | (x & 0xFF_00_00_00) >> 24 for x in colors]
        elif resource_id == '16Bit_1555 color format palette':
            return [transform_color_bitness(x, 1, 5, 5, 5) for x in colors]
        else:
            raise NotImplementedError(f'Palette resource ID {resource_id} is not supported')

    def _colors_internal_to_native(self, resource_id, colors):
        if resource_id == '24BitDos color format palette':
            return [(x & 0xFCFCFC00) >> 10 for x in colors]
        elif resource_id == '24Bit color format palette':
            return [x >> 8 for x in colors]
        elif resource_id == '16Bit_0565 color format palette':
            return [revert_color_bitness(x, 0, 5, 6, 5) for x in colors]
        elif resource_id == '32Bit color format palette':
            # ARGB => RGBA
            return [(x & 0xFF_FF_FF_00) >> 8 | (x & 0xFF) << 24 for x in colors]
        elif resource_id == '16Bit_1555 color format palette':
            return [revert_color_bitness(x, 1, 5, 5, 5) for x in colors]
        else:
            raise NotImplementedError(f'Palette resource ID {resource_id} is not supported')

    def get_child_block_with_data(self, unpacked_data: dict, name: str) -> Tuple['DataBlock', Any]:
        if name == 'last_color_transparent':
            return None, unpacked_data['last_color_transparent']
        return super().get_child_block_with_data(unpacked_data, name)

    def read(self, ctx: ReadContext, name: str = '', read_bytes_amount=None):
        data = super().read(ctx, name, read_bytes_amount)
        # I'm not sure how game decides whether it should draw 255th color transparent or not.
        # It appears that only qfs files in SLIDES/GSLIDES get broken if apply transparency to all bitmaps
        # TODO 16Bit_1555 color format palette has it's own alpha. Turn off last_color_transparent for it?
        data['last_color_transparent'] = (
            not data['resource_id'].startswith('32Bit')
            and len(data['colors']['data']) >= 256
            and 'SLIDES/' not in ctx.ctx_path
        )
        data['colors']['data'] = self._colors_native_to_internal(data['resource_id'], data['colors']['data'])
        return data

    def write(self, data, ctx: WriteContext = None, name: str = ''):
        copied = deepcopy(data)
        copied['colors']['data'] = self._colors_internal_to_native(copied['resource_id'], copied['colors']['data'])
        return super().write(copied, ctx, name)

    def action_invert_colors(self, read_data, **kwargs):
        for i, color in enumerate(read_data['colors']['data']):
            rgb = (color >> 8) & 0xFFFFFF
            alpha = color & 0xFF
            inverted_rgb = rgb ^ 0xFFFFFF
            read_data['colors']['data'][i] = (inverted_rgb << 8) | alpha

    def action_convert_format(self, read_data, color_mode, id, **kwargs):
        current_color_format = read_data['resource_id']
        target_color_format = color_mode
        if current_color_format == target_color_format:
            return
        native = self._colors_internal_to_native(target_color_format, read_data['colors']['data'])
        read_data['colors']['data'] = self._colors_native_to_internal(target_color_format, native)
        read_data['resource_id'] = target_color_format
        read_data['last_color_transparent'] = (
            not read_data['resource_id'].startswith('32Bit')
            and len(read_data['colors']['data']) >= 256
            and 'SLIDES/' not in id
        )


class EacImage(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (
            EnumByteBlock(
                enum_names=[
                    (0x7A, '4Bit'),
                    (0x40, '4Bit PS1'),
                    (0x6D, '16Bit_4444 color format bitmap'),
                    (0x78, '16Bit_0565 color format bitmap'),
                    (0x79, '4Bit (swapped)'),
                    (0x7B, '8Bit'),
                    (0x7E, '16Bit_1555 color format bitmap'),
                    (0x7F, '24Bit color format bitmap'),
                    (0x7D, '32Bit color format bitmap'),
                    (0x60, 'DXT1 compressed bitmap'),
                    (0x61, 'DXT3 compressed bitmap'),
                    (0x62, 'DXT5 compressed bitmap'),
                ]
            ),
            {'description': 'Resource ID'},
        )
        next_offset = (
            IntegerBlock(length=3, is_signed=True, programmatic_value=_stored_next_offset),
            {
                'description': 'Offset from the start of the image to the first block attached to it: the palette '
                'of an 8Bit image, hot spots (0x7C), text (0x6F), and in NFS6 0x69 / 0x70 blocks. Every attached '
                'block starts with its id and the offset to the next one (0 in the last), so they make a chain, '
                'which this parser follows. 0 when nothing is attached (then an 8Bit image uses !pal or !PAL of the '
                'SHPI), never the size of the image block. Recomputed on save when a block parsed into a field is '
                'attached. TNFS has other values in a few car (CFM) and track (FAM) textures without attached blocks: '
                'mostly a negative offset to the !PAL item of the SHPI, sometimes garbage',
            },
        )
        width = (IntegerBlock(length=2), {'usage': 'io,doc', 'description': 'Bitmap width in pixels'})
        height = (IntegerBlock(length=2), {'usage': 'io,doc', 'description': 'Bitmap height in pixels'})
        pivot = (
            Point2D(child=IntegerBlock(length=2, is_signed=True)),
            {
                'description': 'TNFS dashboards add both coordinates to the points of `hot_spots`. y coordinate is '
                'used by the horizon bitmap "horz" of TNFS FAM files when the game scrolls it (horizon "ring type" 0, '
                'the open road tracks by default): this row of the bitmap lies on the horizon line (Win95 SE '
                'FUN_0043ae64). The horizon ring (ring type 1, the closed tracks) does not use it',
            },
        )
        position = (
            Point2D(child=IntegerBlock(length=2)),
            {
                'description': 'Bitmap position on screen. Used for menu/dash sprites. In NFS5 FSH files this is '
                'the position of the image in a texture page (atlas), which is used by CRP models: '
                '12 lower bits of each coordinate are a signed value, 4 higher bits of y are the amount of '
                '`mipmaps` levels (always all of them down to 1x1, 0 without mipmaps), set on save'
            },
        )
        bitmap = (
            BytesBlock(
                length=(
                    lambda ctx: get_bitmap_len(ctx.data('resource_id'), ctx.data('width'), ctx.data('height')),
                    'width * height * pixel_byteness',
                )
            ),
            {
                'usage': 'io,doc',
                'description': 'Pixel color table. For 8Bit bitmap each value represents an index of color in the '
                'attached palette. Palette can be stored: <br/>'
                '- right after 8Bit image<br/>'
                '- as !pal/!PAL in the same SHPI<br/>'
                '- in a different SHPI before this one (if it is WWWW archive)<br/>'
                '- even in different QFS file (TNFS, CONTROL directory).<br/>'
                'Color model is selected according to `resource_id` field. Color models are '
                'described [here](eac_colors.md). DXT1/DXT3/DXT5 bitmaps are S3TC-compressed 4x4 pixel blocks '
                '(8, 16 and 16 bytes per block)',
            },
        )
        mipmaps = (
            TrailingOptionalBlock(
                child=BytesBlock(
                    length=(
                        lambda ctx: mipmaps_byte_len(ctx.data('resource_id'), ctx.data('width'), ctx.data('height')),
                        '(1/4 + 1/16 + 1/64 + etc) * width * height * pixel_byteness',
                    )
                ),
                criteria=(
                    mipmaps_presence_criteria,
                    'dimensions are powers of two and position.y has the amount of levels',
                ),
            ),
            {
                'description': 'Mipmaps pixel data in the same format as `bitmap` field. There are images with '
                'sizes w/2 x h/2, w/4 x h/4, .... up to 1x1, in descending order, each padded with zeros to 16 bytes. '
                'Only NFS5 files have them: the 4 high bits of `position.y` hold the amount of levels'
            },
        )
        pad = (
            TrailingOptionalBlock(
                child=Padding(to=lambda ctx: ctx.data('next_offset'), is_global=False),
                criteria=(image_padding_criteria, 'next_offset points past the pixels'),
            ),
            {
                'description': 'Bytes between the pixels (and mipmaps) and the first attached block: zeros, or '
                'leftovers aligning it',
                'is_unknown': True,
            },
        )
        embedded_palette = (
            TrailingOptionalBlock(
                child=EacPalette(),
                criteria=(chained_block_criteria(PALETTE_IDS, 16), 'the chain of attached blocks has a palette here'),
            ),
            {
                'description': 'Embedded palette, which should be assigned to this bitmap (except for ga00 in TR2_001.FAM)'
            },
        )
        embedded_palette_pad = (
            TrailingOptionalBlock(
                child=BytesBlock(length=(chain_padding_length, 'up to the next attached block')),
                criteria=(chain_padding_criteria, 'the next attached block is 0x7C or 0x6F, not right here'),
            ),
            {'description': 'Bytes between the embedded palette and the next attached block', 'is_unknown': True},
        )
        hot_spots = (
            TrailingOptionalBlock(
                child=ShpiHotSpots(),
                criteria=(chained_block_criteria([HOT_SPOTS_ID], 8), 'the chain of attached blocks has 0x7C here'),
            ),
            {'description': 'Hot spots: points of interest of the bitmap, read by TNFS dashboards'},
        )
        hot_spots_pad = (
            TrailingOptionalBlock(
                child=BytesBlock(length=(chain_padding_length, 'up to the next attached block')),
                criteria=(chain_padding_criteria, 'the next attached block is 0x7C or 0x6F, not right here'),
            ),
            {'description': 'Bytes between the hot spots and the next attached block', 'is_unknown': True},
        )
        text = (
            TrailingOptionalBlock(
                child=ShpiText(),
                criteria=(chained_block_criteria([TEXT_ID], 8), 'the chain of attached blocks has 0x6F here'),
            ),
            {'description': 'Shpi text'},
        )
        embedded_palette_2 = (
            TrailingOptionalBlock(
                child=EacPalette(), criteria=(unlinked_palette_criteria, 'palette header after the end of the chain')
            ),
            {
                'description': 'A palette after the last attached block, which no block links to (some textures '
                'of TNFS TR* tracks)',
                'is_unknown': True,
            },
        )
        embedded_palette_3 = (
            TrailingOptionalBlock(
                child=EacPalette(), criteria=(unlinked_palette_criteria, 'palette header after the end of the chain')
            ),
            {'description': 'One more palette which no block links to', 'is_unknown': True},
        )
        embedded_palette_4 = (
            TrailingOptionalBlock(
                child=EacPalette(), criteria=(unlinked_palette_criteria, 'palette header after the end of the chain')
            ),
            {'description': 'One more palette which no block links to', 'is_unknown': True},
        )

    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'custom_actions': [
                {
                    'method': 'convert_to_4bit',
                    'title': 'Convert to 4bit',
                    'description': 'Converts bitmap to 4bit format.',
                    'is_pure': False,
                    'args': [
                        {
                            'id': 'mode',
                            'title': 'mode',
                            'type': 'enum_string',
                            'choices': ['4Bit', '4Bit PS1', '4Bit (swapped)'],
                        },
                        {
                            'id': 'channel',
                            'title': 'Channel',
                            'type': 'enum_string',
                            'choices': ['alpha', 'RGB', 'red', 'green', 'blue'],
                        },
                    ],
                },
                {
                    'method': 'convert_to_8bit',
                    'title': 'Convert to 8bit',
                    'description': 'Converts bitmap to 8bit format.',
                    'is_pure': False,
                    'args': [
                        {
                            'id': 'channel',
                            'title': 'Channel',
                            'type': 'enum_string',
                            'default': 'generate embedded palette',
                            'choices': ['generate embedded palette', 'alpha', 'RGB', 'red', 'green', 'blue'],
                        },
                        {
                            'id': 'palette_type',
                            'title': 'Palette type',
                            'type': 'enum_string',
                            'default': '32Bit color format palette',
                            'visible_when': {'arg': 'channel', 'value': 'generate embedded palette'},
                            'choices': [
                                '24BitDos color format palette',
                                '24Bit color format palette',
                                '16Bit_0565 color format palette',
                                '32Bit color format palette',
                                '16Bit_1555 color format palette',
                            ],
                        },
                    ],
                },
                {
                    'method': 'convert_to_rgba',
                    'title': 'Convert color model',
                    'description': 'Converts the bitmap to a 16, 24 or 32-bit or a DXT color model. Output colors '
                    'matter for 8Bit and 4Bit bitmaps: "use palette" keeps the colors they show now, '
                    '"transparent-white" makes the index the alpha of white, "black-white" a shade of grey.',
                    'is_pure': False,
                    'args': [
                        {
                            'id': 'color_mode',
                            'title': 'Color mode',
                            'type': 'enum_string',
                            'default': '32Bit color format bitmap',
                            'choices': [
                                '16Bit_4444 color format bitmap',
                                '16Bit_0565 color format bitmap',
                                '16Bit_1555 color format bitmap',
                                '24Bit color format bitmap',
                                '32Bit color format bitmap',
                                'DXT1 compressed bitmap',
                                'DXT3 compressed bitmap',
                                'DXT5 compressed bitmap',
                            ],
                        },
                        {
                            'id': 'output_colors',
                            'title': 'Output colors',
                            'type': 'enum_string',
                            'default': 'use palette',
                            'choices': ['use palette', 'transparent-white', 'black-white'],
                        },
                    ],
                },
                {
                    'method': 'generate_mipmaps',
                    'title': 'Generate mipmaps',
                    'description': 'Generates mipmap levels from the current bitmap (only possible when width and '
                    'height are both powers of two).',
                    'is_pure': False,
                    'args': [],
                },
            ],
        }

    def new_data(self, patch=None):
        data = super().new_data(patch)
        if not (patch or {}).get('resource_id'):
            # a new image is 32-bit, as images added from disk: a lossless start to convert from
            data['resource_id'] = '32Bit color format bitmap'
        if data['width'] == 0 or data['height'] == 0:
            data['width'] = 1
            data['height'] = 1
            if data['resource_id'].startswith('4Bit'):
                data['bitmap'] = [[0]]
            else:
                data['bitmap'] = [0]
        return data

    def estimate_packed_size(self, data, ctx: WriteContext = None):
        length = super().estimate_packed_size(data, ctx)
        # original assumes length if bitmap == length of array, which is not true
        length -= len(data['bitmap'])
        width, height = data['width'], data['height']
        length += get_bitmap_len(data['resource_id'], width, height)
        if data['mipmaps']:
            # same for mipmaps
            length -= len(data['mipmaps'])
            length += mipmaps_byte_len(data['resource_id'], width, height)
        return length

    def _native_to_internal(self, resource_id, width, height, bd):
        if resource_id == '16Bit_4444 color format bitmap':
            bitmap = np.frombuffer(bd, dtype='<u2')
            return [transform_color_bitness(x, 4, 4, 4, 4) for x in bitmap]
        elif resource_id == '16Bit_0565 color format bitmap':
            bitmap = np.frombuffer(bd, dtype='<u2')
            ret = []
            for pxl in bitmap:
                if pxl == 0x7C0:
                    ret.append(0)  # transparent
                else:
                    ret.append(transform_color_bitness(pxl, 0, 5, 6, 5))
            return ret
        elif resource_id.startswith('4Bit'):
            field = ArrayBlock(
                length=height,
                child=SubByteArrayBlock(
                    bits_per_value=4,
                    length=width,
                    value_deserialize_func=(lambda x: 0xFFFFFF00 | transform_bitness(x, 4)),
                    value_serialize_func=lambda x: (x & 0xFF) >> 4,
                ),
            )
            ret = field.unpack(ReadContext(BytesIO(bd)))
            if resource_id == '4Bit (swapped)':
                for row in ret:
                    for i in range(0, len(row), 2):
                        row[i], row[i + 1] = row[i + 1], row[i]
            return ret
        elif resource_id == '8Bit':
            return list(bd)
        elif resource_id == '16Bit_1555 color format bitmap':
            bitmap = np.frombuffer(bd, dtype='<u2')
            return [transform_color_bitness(x, 1, 5, 5, 5) for x in bitmap]
        elif resource_id == '24Bit color format bitmap':
            b4 = bytes(bd)
            b = []
            for i in range(0, len(b4), 3):
                b.extend(b4[i : i + 3])
                b.append(0)
            bitmap = np.frombuffer(bytes(b), dtype='<u4')
            return [int((x << 8) | 0xFF) for x in bitmap]
        elif resource_id == '32Bit color format bitmap':
            bitmap = np.frombuffer(bd, dtype='<u4')
            # ARGB => RGBA
            return [int((x & 0x00_FF_FF_FF) << 8 | (x & 0xFF_00_00_00) >> 24) for x in bitmap]
        elif resource_id.startswith('DXT'):
            return decode_dxt(resource_id[:4], width, height, bd)
        else:
            raise NotImplementedError(f'Bitmap resource ID {resource_id} is not supported')

    def _internal_to_native(self, resource_id, width, height, bd):
        if resource_id == '16Bit_4444 color format bitmap':
            arr = [revert_color_bitness(x, 4, 4, 4, 4) for x in bd]
            return np.asarray(arr, dtype='<u2').tobytes()
        elif resource_id == '16Bit_0565 color format bitmap':
            arr = []
            for pxl in bd:
                if (pxl & 0xFF) < 128:
                    # transparent
                    arr.append(0x7C0)
                else:
                    arr.append(revert_color_bitness(pxl, 0, 5, 6, 5))
            return np.asarray(arr, dtype='<u2').tobytes()
        elif resource_id.startswith('4Bit'):
            field = ArrayBlock(
                length=height,
                child=SubByteArrayBlock(
                    bits_per_value=4,
                    length=width,
                    value_deserialize_func=(lambda x: 0xFFFFFF00 | transform_bitness(x, 4)),
                    value_serialize_func=lambda x: (x & 0xFF) >> 4,
                ),
            )
            if resource_id == '4Bit (swapped)':
                for row in bd:
                    for i in range(0, len(row), 2):
                        row[i], row[i + 1] = row[i + 1], row[i]
            return field.pack(bd)
        elif resource_id == '8Bit':
            return bytes(bd)
        elif resource_id == '16Bit_1555 color format bitmap':
            arr = [revert_color_bitness(x, 1, 5, 5, 5) for x in bd]
            return np.asarray(arr, dtype='<u2').tobytes()
        elif resource_id == '24Bit color format bitmap':
            b4 = np.asarray([x >> 8 for x in bd], dtype='<u4').tobytes()
            return bytes([b for i, b in enumerate(b4) if i % 4 != 3])
        elif resource_id == '32Bit color format bitmap':
            # RGBA => ARGB
            arr = [(x & 0xFF_FF_FF_00) >> 8 | (x & 0xFF) << 24 for x in bd]
            return np.asarray(arr, dtype='<u4').tobytes()
        elif resource_id.startswith('DXT'):
            return encode_dxt(resource_id[:4], width, height, bd)
        else:
            raise NotImplementedError(f'Bitmap resource ID {resource_id} is not supported')

    def _mipmaps_native_to_internal(self, resource_id, width, height, bd):
        """Like `_native_to_internal`, but `bd` is a concatenation of decreasing-size levels, so
        each has to be decoded with its own dimensions rather than the base bitmap's - matters for
        4Bit, whose decoding depends on `width` to know where rows start."""
        result = []
        offset = 0
        for level_width, level_height in mipmap_level_dims(width, height):
            level_len = get_bitmap_len(resource_id, level_width, level_height)
            level_data = self._native_to_internal(
                resource_id, level_width, level_height, bd[offset : offset + level_len]
            )
            result.extend(level_data)
            offset += mipmap_level_byte_len(resource_id, level_width, level_height)
        return result

    def _mipmaps_internal_to_native(self, resource_id, width, height, data):
        """Inverse of `_mipmaps_native_to_internal`."""
        result = b''
        offset = 0
        is_4bit = resource_id.startswith('4Bit')
        for level_width, level_height in mipmap_level_dims(width, height):
            # 4Bit internal data is a list of rows (one row per pixel row); every other format is
            # a flat list of one entry per pixel.
            level_count = level_height if is_4bit else level_width * level_height
            level_data = data[offset : offset + level_count]
            level_bytes = self._internal_to_native(resource_id, level_width, level_height, level_data)
            padding = mipmap_level_byte_len(resource_id, level_width, level_height) - len(level_bytes)
            result += level_bytes + bytes(padding)
            offset += level_count
        return result

    def read(self, ctx: ReadContext, name: str = '', read_bytes_amount=None):
        data = super().read(ctx, name, read_bytes_amount)
        data['bitmap'] = self._native_to_internal(data['resource_id'], data['width'], data['height'], data['bitmap'])
        if data.get('mipmaps'):
            data['mipmaps'] = self._mipmaps_native_to_internal(
                data['resource_id'], data['width'], data['height'], data['mipmaps']
            )
        return data

    # TODO add test which fails now:
    # 1) Open FSH
    # 2) Change color space
    # 3) Save
    # 4) Load updated binary
    # 5) Change color space back
    # 6) Save
    # 7) Compare with original FSH
    @staticmethod
    def _link_chained_blocks(data):
        """Sets the offsets of the chain of attached blocks parsed into fields. The last one keeps its own offset:
        0, or a link to a block the parser keeps as raw bytes, written right after it. Without such fields, a link
        marked by `pad` (a raw block after the padding) follows the pixels too"""
        chained = [name for name in CHAINED_FIELDS if data.get(name) is not None]
        pad = data.get('pad')
        if not chained and pad is None:
            # no link, or a TNFS one to elsewhere (negative, to !PAL, or garbage): written as read
            return
        width, height = data['width'], data['height']
        mipmaps_len = mipmaps_byte_len(data['resource_id'], width, height) if data.get('mipmaps') else 0
        # the first attached block follows the pixels and the padding: one parsed into a field, or one kept as raw
        # bytes (NFS6 0x69 / 0x70) when there is none
        data['next_offset'] = 16 + get_bitmap_len(data['resource_id'], width, height) + mipmaps_len + len(pad or b'')
        if not chained:
            return
        blocks = {'embedded_palette': EacPalette(), 'hot_spots': ShpiHotSpots(), 'text': ShpiText()}
        for name, following in zip(chained, chained[1:]):
            gap = data.get(f'{name}_pad') or b''
            data[name]['next_offset'] = blocks[name].estimate_packed_size(data[name]) + len(gap)
        last = chained[-1]
        if data.get(f'{last}_pad') is not None:
            # padding is read only before a block parsed into a field: that one was removed
            data[f'{last}_pad'] = None
            data[last]['next_offset'] = 0

    @staticmethod
    def _set_mipmap_count(data):
        """Keeps the amount of mipmap levels in `position.y` in sync with `mipmaps`"""
        y = data['position']['y']
        levels = len(list(mipmap_level_dims(data['width'], data['height'])))
        if data.get('mipmaps'):
            data['position']['y'] = (y & 0xFFF) | (levels << 12)
        elif levels and mipmap_count(y) == levels:
            data['position']['y'] = y & 0xFFF

    def write(self, data, ctx: WriteContext = None, name: str = ''):
        copied = deepcopy(data)
        self._set_mipmap_count(copied)
        self._link_chained_blocks(copied)
        copied['bitmap'] = self._internal_to_native(data['resource_id'], data['width'], data['height'], data['bitmap'])
        if copied['mipmaps']:
            copied['mipmaps'] = self._mipmaps_internal_to_native(
                data['resource_id'], data['width'], data['height'], data['mipmaps']
            )
        return super().write(copied, ctx, name)

    def serializer_class(self):
        from serializers import ImageSerializer

        return ImageSerializer

    def _get_channel_mask_offset(self, channel):
        if channel == 'alpha':
            (mask, offs) = (0xFF, 0)
        elif channel == 'red':
            (mask, offs) = (0xFF000000, 24)
        elif channel == 'green':
            (mask, offs) = (0xFF0000, 16)
        elif channel == 'blue':
            (mask, offs) = (0xFF00, 8)
        else:
            raise ValueError(f'Invalid channel: {channel}')
        return mask, offs

    def action_convert_to_4bit(self, read_data, mode, channel, **kwargs):
        current_color_format = read_data['resource_id']
        target_color_format = mode
        if current_color_format == target_color_format:
            return
        width, height = read_data['width'], read_data['height']
        read_data['bitmap'] = self._convert_pixels_to_4bit(
            read_data['bitmap'], current_color_format, channel, [(width, height)]
        )
        if read_data['mipmaps']:
            read_data['mipmaps'] = self._convert_pixels_to_4bit(
                read_data['mipmaps'], current_color_format, channel, list(mipmap_level_dims(width, height))
            )
        if current_color_format == '8Bit':
            self._clear_8bit_palette_fields(read_data)
        read_data['resource_id'] = target_color_format
        return

    def _convert_pixels_to_4bit(self, pixels, current_color_format, channel, level_dims):
        """Converts a flat `bitmap`/`mipmaps` pixel list into the row-shaped representation
        `4Bit` formats use (rows per `level_dims`, see `mipmap_level_dims`)."""
        if current_color_format.startswith('4Bit'):
            return pixels  # already row-shaped
        if current_color_format == '8Bit':

            def transform(pxl):
                return 0xFFFFFF00 | pxl
        elif channel == 'RGB':

            def transform(color):
                r = (color >> 24) & 0xFF
                g = (color >> 16) & 0xFF
                b = (color >> 8) & 0xFF
                return 0xFFFFFF00 | ((r * 77 + g * 150 + b * 29) >> 8)
        else:
            (mask, offs) = self._get_channel_mask_offset(channel)

            def transform(color):
                return 0xFFFFFF00 | ((color & mask) >> offs)

        transformed = [transform(pxl) for pxl in pixels]
        rows = []
        offset = 0
        for level_width, level_height in level_dims:
            for j in range(level_height):
                rows.append(transformed[offset + j * level_width : offset + (j + 1) * level_width])
            offset += level_width * level_height
        return rows

    def _clear_8bit_palette_fields(self, read_data):
        """Clears the trailing palette fields that only apply to 8Bit bitmaps. Their write-time
        presence check only looks at whether they're set, not `resource_id` - stale data here would
        get written anyway and misalign everything read after it."""
        palette = read_data['embedded_palette']
        if palette is not None and all(
            read_data.get(name) is None for name in CHAINED_FIELDS if name != 'embedded_palette'
        ):
            if palette['next_offset'] == 0:
                # the palette was the only attached block
                read_data['next_offset'] = 0
                read_data['pad'] = None
            else:
                # it links to a block kept as raw bytes (NFS6 0x69 / 0x70), which now follows the pixels: marked by
                # the padding, see `_link_chained_blocks`
                read_data['pad'] = read_data.get('pad') or b''
        read_data['embedded_palette'] = None
        read_data['embedded_palette_pad'] = None
        read_data['embedded_palette_2'] = None
        read_data['embedded_palette_3'] = None
        read_data['embedded_palette_4'] = None

    def action_convert_to_8bit(self, read_data, channel, palette_type='32Bit color format palette', id=None, **kwargs):
        current_color_format = read_data['resource_id']
        target_color_format = '8Bit'
        if current_color_format == target_color_format:
            return
        elif current_color_format.startswith('4Bit'):

            def to_index(pxl):
                return pxl & 0xFF

            read_data['bitmap'] = [to_index(pxl) for row in read_data['bitmap'] for pxl in row]
            if read_data['mipmaps']:
                read_data['mipmaps'] = [to_index(pxl) for row in read_data['mipmaps'] for pxl in row]
        elif channel == 'generate embedded palette':
            from PIL import Image
            from resources.eac.utils import quantize_images_to_8bit, build_8bit_palette

            width, height = read_data['width'], read_data['height']

            def to_image(pixels, w, h):
                return Image.frombytes('RGBA', (w, h), b''.join(c.to_bytes(4, 'big') for c in pixels))

            # Mip levels are quantized together with the base bitmap against one shared palette.
            images = [to_image(read_data['bitmap'], width, height)]
            if read_data['mipmaps']:
                offset = 0
                for level_width, level_height in mipmap_level_dims(width, height):
                    count = level_width * level_height
                    images.append(to_image(read_data['mipmaps'][offset : offset + count], level_width, level_height))
                    offset += count

            indices_per_image, packed_palette_colors = quantize_images_to_8bit(images)
            read_data['bitmap'] = indices_per_image[0]
            if read_data['mipmaps']:
                read_data['mipmaps'] = [index for level_indices in indices_per_image[1:] for index in level_indices]
            read_data['embedded_palette'] = build_8bit_palette(
                packed_palette_colors, palette_type, id=join_id(id, 'embedded_palette')
            )
        else:
            if channel == 'RGB':

                def transform(color):
                    r = (color >> 24) & 0xFF
                    g = (color >> 16) & 0xFF
                    b = (color >> 8) & 0xFF
                    return (r * 77 + g * 150 + b * 29) >> 8
            else:
                (mask, offs) = self._get_channel_mask_offset(channel)

                def transform(color):
                    return (color & mask) >> offs

            read_data['bitmap'] = [transform(pxl) for pxl in read_data['bitmap']]
            if read_data['mipmaps']:
                read_data['mipmaps'] = [transform(pxl) for pxl in read_data['mipmaps']]
        read_data['resource_id'] = target_color_format
        return

    def action_convert_to_rgba(self, read_data, color_mode, output_colors, id, **kwargs):
        current_color_format = read_data['resource_id']
        target_color_format = color_mode
        width, height = read_data['width'], read_data['height']

        # Resolved once and shared with the mipmap chain below - both index the same palette.
        palette_colors = None
        if current_color_format == '8Bit' and output_colors == 'use palette':
            from resources.eac.utils import determine_palette_for_8_bit_bitmap

            (palette_block, palette_data) = determine_palette_for_8_bit_bitmap(self, read_data, id)
            if palette_block is not None:
                palette_colors = [c for c in palette_data['colors']['data']]
                if palette_data['last_color_transparent']:
                    palette_colors[255] = 0

        read_data['bitmap'] = self._convert_pixels_to_rgba(
            read_data['bitmap'], current_color_format, target_color_format, output_colors, width, height, palette_colors
        )
        if read_data['mipmaps']:
            # level by level: DXT encodes 4x4 blocks of each level, with its own size
            mipmaps = []
            offset = 0
            for level_width, level_height in mipmap_level_dims(width, height):
                # 4Bit levels are lists of rows, the other formats lists of pixels
                count = level_height if current_color_format.startswith('4Bit') else level_width * level_height
                mipmaps.extend(
                    self._convert_pixels_to_rgba(
                        read_data['mipmaps'][offset : offset + count],
                        current_color_format,
                        target_color_format,
                        output_colors,
                        level_width,
                        level_height,
                        palette_colors,
                    )
                )
                offset += count
            read_data['mipmaps'] = mipmaps
        if current_color_format == '8Bit':
            self._clear_8bit_palette_fields(read_data)
        read_data['resource_id'] = target_color_format

    def _convert_pixels_to_rgba(
        self, pixels, current_color_format, target_color_format, output_colors, width, height, palette_colors
    ):
        """Converts a `bitmap`/`mipmaps` pixel list from `current_color_format` to
        `target_color_format`. `palette_colors`, when given, resolves 8Bit indices to real colors
        for `output_colors == 'use palette'`."""
        new_bitmap8 = []
        if current_color_format.startswith('4Bit'):
            for row in pixels:
                for pxl in row:
                    new_bitmap8.append(pxl & 0xFF)
        elif current_color_format == '8Bit':
            if output_colors == 'use palette':
                if palette_colors is None:
                    new_bitmap8 = pixels
                else:
                    bitmap = []
                    for index in pixels:
                        try:
                            bitmap.append(palette_colors[index])
                        except IndexError:
                            bitmap.append(0)
                    native = self._internal_to_native(target_color_format, width, height, bitmap)
                    return self._native_to_internal(target_color_format, width, height, native)
            else:
                new_bitmap8 = pixels
        else:
            native = self._internal_to_native(target_color_format, width, height, pixels)
            return self._native_to_internal(target_color_format, width, height, native)

        if output_colors in ['transparent-white', 'use palette']:
            return [x | 0xFFFFFF00 for x in new_bitmap8]
        elif output_colors == 'black-white':
            return [(x << 24) | (x << 16) | (x << 8) | 0xFF for x in new_bitmap8]
        else:
            raise ValueError(f'Unknown output_colors value: {output_colors}')

    def _downsample_mip_level(self, resource_id, width, height, values):
        """Produces the next mipmap level (half the dimensions, rounded up) in the same shape as
        `values`. Palette indices (4Bit/8Bit) can't be blended, so they're point-sampled; color
        formats are box-filtered instead."""
        is_4bit = resource_id.startswith('4Bit')
        new_width, new_height = max(1, width // 2), max(1, height // 2)

        def get(x, y):
            x, y = min(x, width - 1), min(y, height - 1)
            return values[y][x] if is_4bit else values[y * width + x]

        if is_4bit or resource_id == '8Bit':
            samples = lambda x, y: [get(2 * x, 2 * y)]
        else:
            samples = lambda x, y: [get(2 * x + dx, 2 * y + dy) for dy in (0, 1) for dx in (0, 1)]

        def pixel(x, y):
            pixels = samples(x, y)
            if len(pixels) == 1:
                return pixels[0]
            r = sum((p >> 24) & 0xFF for p in pixels) // len(pixels)
            g = sum((p >> 16) & 0xFF for p in pixels) // len(pixels)
            b = sum((p >> 8) & 0xFF for p in pixels) // len(pixels)
            a = sum(p & 0xFF for p in pixels) // len(pixels)
            return (r << 24) | (g << 16) | (b << 8) | a

        if is_4bit:
            return [[pixel(x, y) for x in range(new_width)] for y in range(new_height)]
        return [pixel(x, y) for y in range(new_height) for x in range(new_width)]

    def action_generate_mipmaps(self, read_data, **kwargs):
        resource_id, width, height = read_data['resource_id'], read_data['width'], read_data['height']
        if not is_power_of_two(width) or not is_power_of_two(height):
            raise ValueError('Mipmaps can only be generated for images with power-of-two width and height')
        if width == 1 and height == 1:
            raise ValueError('A 1x1 image has no mipmap levels to generate')
        mipmaps = []
        level_values, level_width, level_height = read_data['bitmap'], width, height
        while level_width > 1 or level_height > 1:
            level_values = self._downsample_mip_level(resource_id, level_width, level_height, level_values)
            level_width, level_height = max(1, level_width // 2), max(1, level_height // 2)
            mipmaps.extend(level_values)
        read_data['mipmaps'] = mipmaps
