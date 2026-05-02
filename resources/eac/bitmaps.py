from copy import deepcopy
from typing import Tuple, Any, Dict

from library.context import ReadContext, WriteContext
from library.read_blocks import DataBlock
from library.read_blocks import (DeclarativeCompoundBlock,
                                 IntegerBlock,
                                 SubByteArrayBlock,
                                 BytesBlock,
                                 ArrayBlock,
                                 EnumByteBlock,
                                 EnumLookupDelegateBlock,
                                 )
from library.utils import transform_bitness, extract_number
from resources.eac.fields.misc import Point2D


def transform_color_bitness(color, alpha_bitness, red_bitness, green_bitness, blue_bitness):
    alpha = transform_bitness(extract_number(color, alpha_bitness, red_bitness + green_bitness + blue_bitness),
                              alpha_bitness) if alpha_bitness else 0xFF
    red = transform_bitness(extract_number(color, red_bitness, green_bitness + blue_bitness), red_bitness)
    green = transform_bitness(extract_number(color, green_bitness, blue_bitness), green_bitness)
    blue = transform_bitness(extract_number(color, blue_bitness), blue_bitness)
    return red << 24 | green << 16 | blue << 8 | alpha


def revert_color_bitness(color, alpha_bitness, red_bitness, green_bitness, blue_bitness):
    alpha = (color & 0xff) >> (8 - alpha_bitness)
    red = (color & 0xff000000) >> (32 - red_bitness)
    green = (color & 0xff0000) >> (24 - green_bitness)
    blue = (color & 0xff00) >> (16 - blue_bitness)
    return (alpha << (red_bitness + green_bitness + blue_bitness)
            | red << (green_bitness + blue_bitness)
            | green << blue_bitness
            | blue)


class EacImage(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (EnumByteBlock(enum_names=[(0x6D, '16Bit_4444 color format bitmap'),
                                                 (0x78, '16Bit_0565 color format bitmap'),
                                                 (0x79, '4Bit (swapped)'),
                                                 (0x7A, '4Bit'),
                                                 (0x7B, '8Bit'),
                                                 (0x7E, '16Bit_1555 color format bitmap'),
                                                 (0x7F, '24Bit color format bitmap'),
                                                 (0x7D, '32Bit color format bitmap')]),
                       {'description': 'Resource ID'})
        block_size = (IntegerBlock(length=3),
                      {'description': 'Bitmap block size 16+<pixel_byteness>\\*width\\*height + trailing bytes length'})
        width = (IntegerBlock(length=2),
                 {'usage': 'io,doc',
                  'description': 'Bitmap width in pixels'})
        height = (IntegerBlock(length=2),
                  {'usage': 'io,doc',
                   'description': 'Bitmap height in pixels'})
        pivot = (Point2D(child=IntegerBlock(length=2)),
                 {'is_unknown': True,
                  'description': 'Seems like x coordinate is not used at all. y coordinate is used in horizon '
                                 'textures in TNFS FAM files: higher value = image as horizon will be put higher '
                                 'on the screen. Seems to affect only open tracks'})
        position = (Point2D(child=IntegerBlock(length=2)),
                    {'description': 'Bitmap position on screen. Used for menu/dash sprites. Unknown for others'})
        bitmap = (EnumLookupDelegateBlock(enum_field='resource_id',
                                          blocks=[
                                              ArrayBlock(child=IntegerBlock(length=2),
                                                         length=lambda ctx: ctx.data('width') * ctx.data('height')),
                                              ArrayBlock(child=IntegerBlock(length=2),
                                                         length=lambda ctx: ctx.data('width') * ctx.data('height')),
                                              ArrayBlock(length=lambda ctx: ctx.data('height'),
                                                         child=SubByteArrayBlock(bits_per_value=4,
                                                                                 length=lambda ctx: ctx.data(
                                                                                     '../width'),
                                                                                 value_deserialize_func=lambda
                                                                                     x: 0xFFFFFF00
                                                                                        | transform_bitness(x, 4),
                                                                                 value_serialize_func=lambda x: (
                                                                                                                        x & 0xFF) >> 4)),
                                              ArrayBlock(length=lambda ctx: ctx.data('height'),
                                                         child=SubByteArrayBlock(bits_per_value=4,
                                                                                 length=lambda ctx: ctx.data(
                                                                                     '../width'),
                                                                                 value_deserialize_func=lambda
                                                                                     x: 0xFFFFFF00
                                                                                        | transform_bitness(x, 4),
                                                                                 value_serialize_func=lambda x: (
                                                                                                                        x & 0xFF) >> 4)),
                                              ArrayBlock(child=IntegerBlock(length=1),
                                                         length=lambda ctx: ctx.data('width') * ctx.data('height')),
                                              ArrayBlock(child=IntegerBlock(length=2),
                                                         length=lambda ctx: ctx.data('width') * ctx.data('height')),
                                              ArrayBlock(child=IntegerBlock(length=3),
                                                         length=lambda ctx: ctx.data('width') * ctx.data('height')),
                                              ArrayBlock(child=IntegerBlock(length=4),
                                                         length=lambda ctx: ctx.data('width') * ctx.data('height')),
                                          ]),
                  {'usage': 'io,doc',
                   'description': 'Pixel color table. For 8Bit bitmap each value represents an index of color in the '
                                  'attached palette. Palette can be stored: <br/>'
                                  '- right after 8Bit image<br/>'
                                  '- as !pal/!PAL in the same SHPI<br/>'
                                  '- in a different SHPI before this one (if it is WWWW archive)<br/>'
                                  '- even in different QFS file (TNFS, CONTROL directory).<br/>'
                                  'Color model is selected according to `resource_id` field. Color models are '
                                  'described [here](eac_colors.md)'})

    def read(self, ctx: ReadContext, name: str = '', read_bytes_amount=None):
        data = super().read(ctx, name, read_bytes_amount)
        if data['resource_id'] == '16Bit_4444 color format bitmap':
            data['bitmap']['data'] = [transform_color_bitness(x, 4, 4, 4, 4)
                                      for x in data['bitmap']['data']]
        elif data['resource_id'] == '16Bit_0565 color format bitmap':
            for (i, pxl) in enumerate(data['bitmap']['data']):
                if pxl == 0x7c0:
                    data['bitmap']['data'][i] = 0  # transparent
                else:
                    data['bitmap']['data'][i] = transform_color_bitness(pxl, 0, 5, 6, 5)
        elif data['resource_id'] == '16Bit_1555 color format bitmap':
            data['bitmap']['data'] = [transform_color_bitness(x, 1, 5, 5, 5)
                                      for x in data['bitmap']['data']]
        elif data['resource_id'] == '24Bit color format bitmap':
            data['bitmap']['data'] = [(x << 8) | 0xFF for x in data['bitmap']['data']]
        elif data['resource_id'] == '32Bit color format bitmap':
            # ARGB => RGBA
            data['bitmap']['data'] = [(x & 0x00_ff_ff_ff) << 8 | (x & 0xff_00_00_00) >> 24 for x in
                                      data['bitmap']['data']]
        elif data['resource_id'] == '4Bit (swapped)':
            for row in data['bitmap']['data']:
                for i in range(0, len(row), 2):
                    row[i], row[i + 1] = row[i + 1], row[i]
        elif data['resource_id'] in ['4Bit', '8Bit']:
            pass
        else:
            raise NotImplementedError(f"Bitmap resource ID {data['resource_id']} is not supported")
        return data

    # TODO add test which fails now:
    # 1) Open FSH
    # 2) Change color space
    # 3) Save
    # 4) Load updated binary
    # 5) Change color space back
    # 6) Save
    # 7) Compare with original FSH
    def write(self, data, ctx: WriteContext = None, name: str = ''):
        copied = deepcopy(data)
        if copied['resource_id'] == '16Bit_4444 color format bitmap':
            copied['bitmap']['data'] = [revert_color_bitness(x, 4, 4, 4, 4) for x in copied['bitmap']['data']]
        elif copied['resource_id'] == '16Bit_0565 color format bitmap':
            for (i, pxl) in enumerate(copied['bitmap']['data']):
                if (pxl & 0xff) < 128:
                    # transparent
                    copied['bitmap']['data'][i] = 0x7c0
                else:
                    copied['bitmap']['data'][i] = revert_color_bitness(pxl, 0, 5, 6, 5)
        elif copied['resource_id'] == '16Bit_1555 color format bitmap':
            copied['bitmap']['data'] = [revert_color_bitness(x, 1, 5, 5, 5) for x in copied['bitmap']['data']]
        elif copied['resource_id'] == '24Bit color format bitmap':
            copied['bitmap']['data'] = [x >> 8 for x in copied['bitmap']['data']]
        elif copied['resource_id'] == '32Bit color format bitmap':
            # RGBA => ARGB
            copied['bitmap']['data'] = [(x & 0xff_ff_ff_00) >> 8 | (x & 0xff) << 24 for x in copied['bitmap']['data']]
        elif copied['resource_id'] == '4Bit (swapped)':
            for row in copied['bitmap']['data']:
                for i in range(0, len(row), 2):
                    row[i], row[i + 1] = row[i + 1], row[i]
        elif copied['resource_id'] in ['4Bit', '8Bit']:
            pass
        else:
            raise NotImplementedError(f"Bitmap resource ID {copied['resource_id']} is not supported")
        return super().write(copied, ctx, name)

    def serializer_class(self):
        from serializers import ImageSerializer
        return ImageSerializer


class EacPalette(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (EnumByteBlock(enum_names=[(0x22, '24BitDos color format palette'),
                                                 (0x24, '24Bit color format palette'),
                                                 (0x29, '16BitUnk color format palette'),
                                                 (0x2A, '32Bit color format palette'),
                                                 # TODO colors 15-0 ? found here https://bitbucket.org/fifam/otools/src/master/OTools/Fsh/Fsh.h
                                                 (0x2D, '16Bit_0565 color format palette')]),
                       {'description': 'Resource ID'})
        unk0 = (BytesBlock(length=3),
                {'is_unknown': True})
        num_colors = (IntegerBlock(length=2,
                                   programmatic_value=lambda ctx: len(ctx.data('colors/data'))),
                      {'description': 'Amount of colors'})
        unk1 = (BytesBlock(length=2),
                {'is_unknown': True})
        num_colors1 = (IntegerBlock(length=2,
                                    programmatic_value=lambda ctx: len(ctx.data('colors/data'))),
                       {'description': 'Always equals to num_colors?'})
        unk2 = (BytesBlock(length=6),
                {'is_unknown': True})
        colors = (EnumLookupDelegateBlock(enum_field='resource_id',
                                          blocks=[
                                              ArrayBlock(length=lambda ctx: ctx.data('num_colors'),
                                                         child=IntegerBlock(length=3, byte_order='big')),
                                              ArrayBlock(length=lambda ctx: ctx.data('num_colors'),
                                                         child=IntegerBlock(length=3, byte_order='big')),
                                              ArrayBlock(length=lambda ctx: ctx.data('num_colors'),
                                                         child=IntegerBlock(length=2)),
                                              ArrayBlock(length=lambda ctx: ctx.data('num_colors'),
                                                         child=IntegerBlock(length=4)),
                                              ArrayBlock(length=lambda ctx: ctx.data('num_colors'),
                                                         child=IntegerBlock(length=2))
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
        data = super().read(ctx, name, read_bytes_amount)
        if data.get('num_colors') is not None:
            assert data['num_colors'] == data['num_colors1']
        # I'm not sure how game decides whether it should draw 255th color transparent or not.
        # It appears that only qfs files in SLIDES/GSLIDES get broken if apply transparency to all bitmaps
        data['last_color_transparent'] = not data['resource_id'].startswith('32Bit') and len(
            data['colors']['data']) >= 256 and 'SLIDES/' not in ctx.ctx_path
        if data['resource_id'] == '24BitDos color format palette':
            data['colors']['data'] = [(x & 0x3F3F3F) << 10 | 255 for x in data['colors']['data']]
        elif data['resource_id'] == '24Bit color format palette':
            data['colors']['data'] = [x << 8 | 0xFF for x in data['colors']['data']]
        elif data['resource_id'] == '16BitUnk color format palette':
            data['colors']['data'] = [transform_color_bitness(x, 0, 5, 6, 5) for x in data['colors']['data']]
        elif data['resource_id'] == '32Bit color format palette':
            # ARGB => RGBA
            for (i, pxl) in enumerate(data['colors']['data']):
                data['colors']['data'][i] = (pxl & 0x00_ff_ff_ff) << 8 | (pxl & 0xff_00_00_00) >> 24
        elif data['resource_id'] == '16Bit_0565 color format palette':
            for (i, pxl) in enumerate(data['colors']['data']):
                if pxl == 0x7c0:
                    data['colors']['data'][i] = 0  # transparent
                else:
                    data['colors']['data'][i] = transform_color_bitness(pxl, 0, 5, 6, 5)
        else:
            raise NotImplementedError(f"Palette resource ID {data['resource_id']} is not supported")
        return data

    def write(self, data, ctx: WriteContext = None, name: str = ''):
        copied = deepcopy(data)
        if copied['resource_id'] == '24BitDos color format palette':
            copied['colors']['data'] = [(x & 0xFCFCFC00) >> 10 for x in copied['colors']['data']]
        elif copied['resource_id'] == '24Bit color format palette':
            copied['colors']['data'] = [x >> 8 for x in copied['colors']['data']]
        elif copied['resource_id'] == '16BitUnk color format palette':
            for (i, pxl) in enumerate(copied['colors']['data']):
                red = (pxl & 0xff000000) >> 27
                green = (pxl & 0xff0000) >> 18
                blue = (pxl & 0xff00) >> 11
                copied['colors']['data'][i] = red << 11 | green << 5 | blue
        elif copied['resource_id'] == '32Bit color format palette':
            # RGBA => ARGB
            for (i, pxl) in enumerate(copied['colors']['data']):
                copied['colors']['data'][i] = (pxl & 0xff_ff_ff_00) >> 8 | (pxl & 0xff) << 24
        elif copied['resource_id'] == '16Bit_0565 color format palette':
            for (i, pxl) in enumerate(copied['colors']['data']):
                if (pxl & 0xff) < 128:
                    # transparent
                    copied['colors']['data'][i] = 0x7c0
                else:
                    red = (pxl & 0xff000000) >> 27
                    green = (pxl & 0xff0000) >> 18
                    blue = (pxl & 0xff00) >> 11
                    copied['colors']['data'][i] = red << 11 | green << 5 | blue
        else:
            raise NotImplementedError(f"Palette resource ID {copied['resource_id']} is not supported")
        return super().write(copied, ctx, name)
