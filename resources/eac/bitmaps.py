from copy import deepcopy

from library.context import ReadContext, WriteContext
from library.read_blocks import (DeclarativeCompoundBlock,
                                 IntegerBlock,
                                 SubByteArrayBlock,
                                 BytesBlock,
                                 ArrayBlock,
                                 EnumByteBlock,
                                 EnumLookupDelegateBlock,
                                 )
from library.utils import transform_bitness, transform_color_bitness


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
                      {
                          'description': 'Bitmap block size 16+<color_bytes_amount>\\*width\\*height + trailing bytes length'})
        width = (IntegerBlock(length=2),
                 {'description': 'Bitmap width in pixels'})
        height = (IntegerBlock(length=2),
                  {'description': 'Bitmap height in pixels'})
        unk = (BytesBlock(length=2),
               {'is_unknown': True})
        pivot_y = (IntegerBlock(length=2),
                   {'description': 'For "horz" bitmap in TNFS FAM files: Y coordinate of the horizon line on '
                                   'the image. Higher value = image as horizon will be put higher on the screen. '
                                   'Seems to affect only open tracks'})
        x = (IntegerBlock(length=2),
             {'description': 'X coordinate of bitmap position on screen. Used for menu/dash sprites'})
        y = (IntegerBlock(length=2),
             {'description': 'Y coordinate of bitmap position on screen. Used for menu/dash sprites'})
        bitmap = (EnumLookupDelegateBlock(enum_field='resource_id',
                                          blocks=[
                                              ArrayBlock(child=IntegerBlock(length=2),
                                                         length=lambda ctx: ctx.data('width') * ctx.data('height')),
                                              ArrayBlock(child=IntegerBlock(length=2),
                                                         length=lambda ctx: ctx.data('width') * ctx.data('height')),
                                              ArrayBlock(length=lambda ctx: ctx.data('height'),
                                                         child=SubByteArrayBlock(bits_per_value=4,
                                                                                 length=lambda ctx: ctx.data('../width'),
                                                                                 value_deserialize_func=lambda x: 0xFFFFFF00
                                                                                                                  | transform_bitness(x, 4),
                                                                                 value_serialize_func=lambda x: (x & 0xFF) >> 4)),
                                              ArrayBlock(length=lambda ctx: ctx.data('height'),
                                                         child=SubByteArrayBlock(bits_per_value=4,
                                                                                 length=lambda ctx: ctx.data('../width'),
                                                                                 value_deserialize_func=lambda x: 0xFFFFFF00
                                                                                                                  | transform_bitness(x, 4),
                                                                                 value_serialize_func=lambda x: (x & 0xFF) >> 4)),
                                              ArrayBlock(child=IntegerBlock(length=1),
                                                         length=lambda ctx: ctx.data('width') * ctx.data('height')),
                                              ArrayBlock(child=IntegerBlock(length=2),
                                                         length=lambda ctx: ctx.data('width') * ctx.data('height')),
                                              ArrayBlock(child=IntegerBlock(length=3),
                                                         length=lambda ctx: ctx.data('width') * ctx.data('height')),
                                              ArrayBlock(child=IntegerBlock(length=4),
                                                         length=lambda ctx: ctx.data('width') * ctx.data('height')),
                                          ]),
                  {'description': 'Pixel color table. For 8Bit bitmap each value represents an index of color in the '
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
            data['bitmap']['data'] = [x << 8 | 0xFF for x in data['bitmap']['data']]
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
            for (i, pxl) in enumerate(copied['bitmap']['data']):
                alpha = (pxl & 0xff) >> 4
                red = (pxl & 0xff000000) >> 28
                green = (pxl & 0xff0000) >> 20
                blue = (pxl & 0xff00) >> 12
                copied['bitmap']['data'][i] = alpha << 12 | red << 8 | green << 4 | blue
        elif copied['resource_id'] == '16Bit_0565 color format bitmap':
            for (i, pxl) in enumerate(copied['bitmap']['data']):
                if (pxl & 0xff) < 128:
                    pxl = 0x00_FB_00_FF  # transparent
                red = (pxl & 0xff000000) >> 27
                green = (pxl & 0xff0000) >> 18
                blue = (pxl & 0xff00) >> 11
                copied['bitmap']['data'][i] = red << 11 | green << 5 | blue
        elif copied['resource_id'] == '16Bit_1555 color format bitmap':
            for (i, pxl) in enumerate(copied['bitmap']['data']):
                red = (pxl & 0xff000000) >> 27
                green = (pxl & 0xff0000) >> 18
                blue = (pxl & 0xff00) >> 11
                alpha = pxl & 0xff >> 7
                copied['bitmap']['data'][i] = alpha << 15 | red << 10 | green << 5 | blue
        elif copied['resource_id'] == '24Bit color format bitmap':
            copied['bitmap']['data'] = [x >> 8 | 0xFF for x in copied['bitmap']['data']]
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
        from serializers import BitmapSerializer
        return BitmapSerializer
