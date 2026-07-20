from copy import deepcopy
from functools import lru_cache
from io import BytesIO
from typing import Tuple, Any, Dict

import numpy as np
from math import ceil

from library.context import ReadContext, WriteContext
from library.read_blocks import (DataBlock,
                                 DeclarativeCompoundBlock,
                                 IntegerBlock,
                                 SubByteArrayBlock,
                                 BytesBlock,
                                 ArrayBlock,
                                 EnumByteBlock,
                                 EnumLookupDelegateBlock,
                                 )
from library.utils import transform_bitness, extract_number
from resources.eac.fields.misc import Point2D


@lru_cache(maxsize=256)
def transform_color_bitness(color, alpha_bitness, red_bitness, green_bitness, blue_bitness):
    alpha = transform_bitness(extract_number(color, alpha_bitness, red_bitness + green_bitness + blue_bitness),
                              alpha_bitness) if alpha_bitness else 0xFF
    red = transform_bitness(extract_number(color, red_bitness, green_bitness + blue_bitness), red_bitness)
    green = transform_bitness(extract_number(color, green_bitness, blue_bitness), green_bitness)
    blue = transform_bitness(extract_number(color, blue_bitness), blue_bitness)
    return int(red << 24 | green << 16 | blue << 8 | alpha)


@lru_cache(maxsize=256)
def revert_color_bitness(color, alpha_bitness, red_bitness, green_bitness, blue_bitness):
    alpha = (color & 0xff) >> (8 - alpha_bitness)
    red = (color & 0xff000000) >> (32 - red_bitness)
    green = (color & 0xff0000) >> (24 - green_bitness)
    blue = (color & 0xff00) >> (16 - blue_bitness)
    return (alpha << (red_bitness + green_bitness + blue_bitness)
            | red << (green_bitness + blue_bitness)
            | green << blue_bitness
            | blue)


def get_bitmap_len(resource_id, width, height):
    if resource_id[:2] == '16':
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


class EacImage(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (EnumByteBlock(enum_names=[(0x7A, '4Bit'),
                                                 (0x40, '4Bit PS1'),
                                                 (0x6D, '16Bit_4444 color format bitmap'),
                                                 (0x78, '16Bit_0565 color format bitmap'),
                                                 (0x79, '4Bit (swapped)'),
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
        bitmap = (BytesBlock(
            length=(lambda ctx: get_bitmap_len(ctx.data('resource_id'), ctx.data('width'), ctx.data('height')),
                    'width * height * pixel_byteness')),
                  {'usage': 'io,doc',
                   'description': 'Pixel color table. For 8Bit bitmap each value represents an index of color in the '
                                  'attached palette. Palette can be stored: <br/>'
                                  '- right after 8Bit image<br/>'
                                  '- as !pal/!PAL in the same SHPI<br/>'
                                  '- in a different SHPI before this one (if it is WWWW archive)<br/>'
                                  '- even in different QFS file (TNFS, CONTROL directory).<br/>'
                                  'Color model is selected according to `resource_id` field. Color models are '
                                  'described [here](eac_colors.md)'})

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
                            'choices': ['4Bit',
                                        '4Bit PS1',
                                        '4Bit (swapped)']
                        },
                        {
                            'id': 'channel',
                            'title': 'Channel',
                            'type': 'enum_string',
                            'choices': ['alpha', 'RGB', 'red', 'green', 'blue']
                        }
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
                            'choices': ['alpha', 'RGB', 'red', 'green', 'blue']
                        }
                    ],
                },
                {
                    'method': 'convert_to_rgba',
                    'title': 'Convert to RGBA',
                    'description': 'Converts bitmap to RGBA format.',
                    'is_pure': False,
                    'args': [
                        {
                            'id': 'color_mode',
                            'title': 'Color mode',
                            'type': 'enum_string',
                            'default': '32Bit color format bitmap',
                            'choices': ['16Bit_4444 color format bitmap',
                                        '16Bit_0565 color format bitmap',
                                        '16Bit_1555 color format bitmap',
                                        '24Bit color format bitmap',
                                        '32Bit color format bitmap']
                        },
                        {
                            'id': 'output_colors',
                            'title': 'Output colors',
                            'type': 'enum_string',
                            'default': 'use palette',
                            'choices': ['use palette', 'transparent-white', 'black-white']
                        }
                    ],
                }
            ]
        }

    def new_data(self, patch=None):
        data = super().new_data()
        data['width'] = 1
        data['height'] = 1
        data['bitmap'] = [[0]]
        return data

    def estimate_packed_size(self, data, ctx: WriteContext = None):
        length = super().estimate_packed_size(data, ctx)
        # original assumes length if bitmap == length of array, which is not true
        length -= len(data['bitmap'])
        length += get_bitmap_len(data['resource_id'], data['width'], data['height'])
        return length

    def _native_to_internal(self, resource_id, width, height, bd):
        if resource_id == '16Bit_4444 color format bitmap':
            bitmap = np.frombuffer(bd, dtype='<u2')
            return [transform_color_bitness(x, 4, 4, 4, 4) for x in bitmap]
        elif resource_id == '16Bit_0565 color format bitmap':
            bitmap = np.frombuffer(bd, dtype='<u2')
            ret = []
            for pxl in bitmap:
                if pxl == 0x7c0:
                    ret.append(0)  # transparent
                else:
                    ret.append(transform_color_bitness(pxl, 0, 5, 6, 5))
            return ret
        elif resource_id.startswith('4Bit'):
            field = ArrayBlock(length=height,
                               child=SubByteArrayBlock(bits_per_value=4,
                                                       length=width,
                                                       value_deserialize_func=(lambda x:
                                                                               0xFFFFFF00
                                                                               | transform_bitness(x, 4)),
                                                       value_serialize_func=lambda x: (x & 0xFF) >> 4))
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
            return [transform_color_bitness(x, 1, 5, 5, 5)
                    for x in bitmap]
        elif resource_id == '24Bit color format bitmap':
            b4 = bytes(bd)
            b = []
            for i in range(0, len(b4), 3):
                b.extend(b4[i:i + 3])
                b.append(0)
            bitmap = np.frombuffer(bytes(b), dtype='<u4')
            return [int((x << 8) | 0xFF) for x in bitmap]
        elif resource_id == '32Bit color format bitmap':
            bitmap = np.frombuffer(bd, dtype='<u4')
            # ARGB => RGBA
            return [int((x & 0x00_ff_ff_ff) << 8 | (x & 0xff_00_00_00) >> 24) for x in bitmap]
        else:
            raise NotImplementedError(f"Bitmap resource ID {resource_id} is not supported")

    def _internal_to_native(self, resource_id, width, height, bd):
        if resource_id == '16Bit_4444 color format bitmap':
            arr = [revert_color_bitness(x, 4, 4, 4, 4) for x in bd]
            return np.asarray(arr, dtype='<u2').tobytes()
        elif resource_id == '16Bit_0565 color format bitmap':
            arr = []
            for pxl in bd:
                if (pxl & 0xff) < 128:
                    # transparent
                    arr.append(0x7c0)
                else:
                    arr.append(revert_color_bitness(pxl, 0, 5, 6, 5))
            return np.asarray(arr, dtype='<u2').tobytes()
        elif resource_id.startswith('4Bit'):
            field = ArrayBlock(length=height,
                               child=SubByteArrayBlock(bits_per_value=4,
                                                       length=width,
                                                       value_deserialize_func=(lambda x:
                                                                               0xFFFFFF00
                                                                               | transform_bitness(x, 4)),
                                                       value_serialize_func=lambda x: (x & 0xFF) >> 4))
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
            arr = [(x & 0xff_ff_ff_00) >> 8 | (x & 0xff) << 24 for x in bd]
            return np.asarray(arr, dtype='<u4').tobytes()
        else:
            raise NotImplementedError(f"Bitmap resource ID {resource_id} is not supported")

    def read(self, ctx: ReadContext, name: str = '', read_bytes_amount=None):
        data = super().read(ctx, name, read_bytes_amount)
        data['bitmap'] = self._native_to_internal(data['resource_id'], data['width'], data['height'], data['bitmap'])
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
        copied['bitmap'] = self._internal_to_native(data['resource_id'], data['width'], data['height'], data['bitmap'])
        return super().write(copied, ctx, name)

    def serializer_class(self):
        from serializers import ImageSerializer
        return ImageSerializer

    def _get_channel_mask_offset(self, channel):
        if channel == 'alpha':
            (mask, offs) = (0xff, 0)
        elif channel == 'red':
            (mask, offs) = (0xff000000, 24)
        elif channel == 'green':
            (mask, offs) = (0xff0000, 16)
        elif channel == 'blue':
            (mask, offs) = (0xff00, 8)
        else:
            raise ValueError(f'Invalid channel: {channel}')
        return mask, offs

    def action_convert_to_4bit(self, read_data, mode, channel, **kwargs):
        current_color_format = read_data['resource_id']
        target_color_format = mode
        if current_color_format == target_color_format:
            return
        elif current_color_format == '8Bit':
            new_bitmap = []
            for j in range(read_data['height']):
                new_bitmap.append([])
                for i in range(read_data['width']):
                    pxl = read_data['bitmap'][j * read_data['width'] + i]
                    new_bitmap[j].append(0xffffff00 | pxl)
            read_data['bitmap'] = new_bitmap
        elif current_color_format.startswith('4Bit'):
            pass
        else:
            if channel == 'RGB':
                def transform(color):
                    r = (color >> 24) & 0xFF
                    g = (color >> 16) & 0xFF
                    b = (color >> 8) & 0xFF
                    return 0xffffff00 | ((r * 77 + g * 150 + b * 29) >> 8)
            else:
                (mask, offs) = self._get_channel_mask_offset(channel)

                def transform(color):
                    return 0xffffff00 | ((color & mask) >> offs)
            new_bitmap = []
            for j in range(read_data['height']):
                new_bitmap.append([])
                for i in range(read_data['width']):
                    pxl = read_data['bitmap'][j * read_data['width'] + i]
                    new_bitmap[j].append(transform(pxl))
            read_data['bitmap'] = new_bitmap
        read_data['resource_id'] = target_color_format
        return

    def action_convert_to_8bit(self, read_data, channel, **kwargs):
        current_color_format = read_data['resource_id']
        target_color_format = '8Bit'
        if current_color_format == target_color_format:
            return
        elif current_color_format.startswith('4Bit'):
            new_bitmap = []
            for j in range(read_data['height']):
                for i in range(read_data['width']):
                    pxl = read_data['bitmap'][j][i]
                    new_bitmap.append(pxl & 0xff)
            read_data['bitmap'] = new_bitmap
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
        read_data['resource_id'] = target_color_format
        return

    def action_convert_to_rgba(self, read_data, color_mode, output_colors, id, **kwargs):
        current_color_format = read_data['resource_id']
        target_color_format = color_mode
        new_bitmap8 = []
        if current_color_format.startswith('4Bit'):
            for j in range(read_data['height']):
                for i in range(read_data['width']):
                    pxl = read_data['bitmap'][j][i]
                    new_bitmap8.append(pxl & 0xff)
        elif current_color_format == '8Bit':
            if output_colors == 'use palette':
                from resources.eac.utils import determine_palette_for_8_bit_bitmap
                (palette_block, palette_data) = determine_palette_for_8_bit_bitmap(self, read_data, id)
                bitmap = []
                if palette_block is None:
                    new_bitmap8 = read_data['bitmap']
                else:
                    palette_colors = [c for c in palette_data['colors']['data']]
                    if palette_data['last_color_transparent']:
                        palette_colors[255] = 0
                    for index in read_data['bitmap']:
                        try:
                            bitmap.append(palette_colors[index])
                        except IndexError:
                            bitmap.append(0)
                    native = self._internal_to_native(target_color_format, read_data['width'], read_data['height'],
                                                      bitmap)
                    read_data['bitmap'] = self._native_to_internal(target_color_format, read_data['width'],
                                                                   read_data['height'],
                                                                   native)
            else:
                new_bitmap8 = read_data['bitmap']
        else:
            native = self._internal_to_native(target_color_format, read_data['width'], read_data['height'],
                                              read_data['bitmap'])
            read_data['bitmap'] = self._native_to_internal(target_color_format, read_data['width'], read_data['height'],
                                                           native)
        if new_bitmap8:
            if output_colors in ['transparent-white', 'use palette']:
                read_data['bitmap'] = [x | 0xffffff00 for x in new_bitmap8]
            elif output_colors == 'black-white':
                read_data['bitmap'] = [(x << 24) | (x << 16) | (x << 8) | 0xff for x in new_bitmap8]
            else:
                raise ValueError(f'Unknown output_colors value: {output_colors}')
        read_data['resource_id'] = target_color_format


class EacPalette(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (EnumByteBlock(enum_names=[(0x22, '24BitDos color format palette'),
                                                 (0x24, '24Bit color format palette'),
                                                 (0x29, '16Bit_0565 color format palette'),
                                                 (0x2A, '32Bit color format palette'),
                                                 # TODO colors 15-0 ? found here https://bitbucket.org/fifam/otools/src/master/OTools/Fsh/Fsh.h
                                                 (0x2D, '16Bit_1555 color format palette')]),
                       {'description': 'Resource ID'})
        unk0 = (BytesBlock(length=3),
                {'is_unknown': True})
        num_colors = (IntegerBlock(length=2,
                                   programmatic_value=lambda ctx: len(ctx.data('colors/data'))),
                      {'usage': 'io,doc',
                       'description': 'Amount of colors'})
        unk1 = (BytesBlock(length=2),
                {'is_unknown': True})
        num_colors1 = (IntegerBlock(length=2,
                                    programmatic_value=lambda ctx: len(ctx.data('colors/data'))),
                       {'usage': 'io,doc',
                        'description': 'Always equals to num_colors?'})
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
                    'args': [{
                        'id': 'color_mode',
                        'title': 'Color mode',
                        'type': 'enum_string',
                        'choices': ['24BitDos color format palette',
                                    '24Bit color format palette',
                                    '16Bit_0565 color format palette',
                                    '32Bit color format palette',
                                    '16Bit_1555 color format palette']
                    }],
                }
            ],
            'block_description': 'Resource with colors LUT (look-up table). EA 8-bit bitmaps have 1-byte value per pixel, '
                                 'meaning the index of color in LUT of assigned palette. Has special colors: '
                                 '255th in most cases means transparent color, 254th in car textures is replaced by '
                                 'tail light color, 250th - 253th in car textures are rendered black: thy are reserved '
                                 'for cop car siren',
        }

    def new_data(self, patch=None):
        return {**super().new_data(),
                'last_color_transparent': False}

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
            return [(x & 0x00_ff_ff_ff) << 8 | (x & 0xff_00_00_00) >> 24 for x in colors]
        elif resource_id == '16Bit_1555 color format palette':
            return [transform_color_bitness(x, 1, 5, 5, 5) for x in colors]
        else:
            raise NotImplementedError(f"Palette resource ID {resource_id} is not supported")

    def _colors_internal_to_native(self, resource_id, colors):
        if resource_id == '24BitDos color format palette':
            return [(x & 0xFCFCFC00) >> 10 for x in colors]
        elif resource_id == '24Bit color format palette':
            return [x >> 8 for x in colors]
        elif resource_id == '16Bit_0565 color format palette':
            return [revert_color_bitness(x, 0, 5, 6, 5) for x in colors]
        elif resource_id == '32Bit color format palette':
            # ARGB => RGBA
            return [(x & 0xff_ff_ff_00) >> 8 | (x & 0xff) << 24 for x in colors]
        elif resource_id == '16Bit_1555 color format palette':
            return [revert_color_bitness(x, 1, 5, 5, 5) for x in colors]
        else:
            raise NotImplementedError(f"Palette resource ID {resource_id} is not supported")

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
        # TODO 16Bit_1555 color format palette has it's own alpha. Turn off last_color_transparent for it?
        data['last_color_transparent'] = not data['resource_id'].startswith('32Bit') and len(
            data['colors']['data']) >= 256 and 'SLIDES/' not in ctx.ctx_path
        data['colors']['data'] = self._colors_native_to_internal(data['resource_id'], data['colors']['data'])
        return data

    def write(self, data, ctx: WriteContext = None, name: str = ''):
        copied = deepcopy(data)
        copied['colors']['data'] = self._colors_internal_to_native(copied['resource_id'], copied['colors']['data'])
        return super().write(copied, ctx, name)

    def action_invert_colors(self, read_data, **kwargs):
        for (i, color) in enumerate(read_data['colors']['data']):
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
        read_data['last_color_transparent'] = not read_data['resource_id'].startswith('32Bit') and len(
            read_data['colors']['data']) >= 256 and 'SLIDES/' not in id
