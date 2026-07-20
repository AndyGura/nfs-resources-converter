import traceback
from io import SEEK_CUR
from typing import Dict

from library.context import ReadContext, WriteContext
from library.read_blocks import (CompoundBlock,
                                 DeclarativeCompoundBlock,
                                 UTF8Block,
                                 IntegerBlock,
                                 ArrayBlock,
                                 AutoDetectBlock,
                                 BytesBlock, LengthPrefixedArrayBlock)
from library.read_blocks.archives import ArchiveBlock
from library.read_blocks.misc.value_validators import Eq
from library.utils.id import join_id
from resources.eac.bitmaps import EacImage, EacPalette
from resources.eac.misc import ShpiText


def determine_shpi_length(ctx):
    try:
        return ctx.read_bytes_remaining
    except Exception:
        return ctx.data('length') - 16 - 8 * ctx.data('num_items')


class PaletteReference(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (IntegerBlock(length=1, value_validator=Eq(0x7C)),
                       {'description': 'Resource ID'})
        unk0 = (BytesBlock(length=3),
                {'is_unknown': True})
        unk1 = (LengthPrefixedArrayBlock(length_block=(IntegerBlock(length=4)),
                                         child=BytesBlock(length=8)),
                {'is_unknown': True})

    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Unknown resource. Happens after 8-bit bitmap, which does not contain embedded palette. '
                                 'Probably a reference to palette which should be used, that\'s why named so',
        }


class ShpiBlock(ArchiveBlock):

    @property
    def schema(self) -> Dict:
        return {**super().schema,
                'block_description': 'A container of images and palettes for them',
                'custom_actions': [{
                    'method': 'convert_to_8bit',
                    'title': 'Convert all images to 8Bit',
                    'description': 'Quantize all images in this SHPI block to 8-bit with single palette',
                    'is_pure': False,
                    'args': [
                        {
                            'id': 'palette_name',
                            'title': 'Palette name',
                            'type': 'string',
                            'default': '!pal'
                        },
                        {
                            'id': 'palette_type',
                            'title': 'Palette type',
                            'type': 'enum_string',
                            'choices': ['24BitDos color format palette',
                                        '24Bit color format palette',
                                        '16Bit_0565 color format palette',
                                        '32Bit color format palette',
                                        '16Bit_1555 color format palette']
                        },
                        {
                            'id': 'num_colors',
                            'title': 'Max number of colors',
                            'description': 'Maximum number of colors in the palette. Last transparent color is included',
                            'type': 'number',
                            'default': 256
                        }
                    ],
                }]}

    def __init__(self, **kwargs):
        super().__init__(item_block=AutoDetectBlock(possible_blocks=[
            EacImage(),
            EacPalette(),
            PaletteReference(),
            ShpiText(),
            BytesBlock(length=(lambda ctx: next(x for x in (
                x['offset'] - ctx.local_buffer_pos
                for x in (sorted(ctx.data('items_descr'), key=lambda x: x['offset'])
                          + [{'offset': ctx.read_bytes_amount}])
            ) if x > 0), 'item_length'))]),
            alias_field=UTF8Block(length=4),
            **kwargs)

    class Fields(ArchiveBlock.Fields):
        resource_id = (UTF8Block(length=4, value_validator=Eq('SHPI')),
                       {'description': 'Resource ID'})
        length = (IntegerBlock(length=4,
                               programmatic_value=lambda ctx: ctx.block.estimate_packed_size(ctx.get_full_data())),
                  {'description': 'The length of this SHPI block in bytes'})
        num_items = (IntegerBlock(length=4,
                                  programmatic_value=lambda ctx: len(ctx.data('items_descr'))),
                     {'usage': 'io,doc',
                      'description': 'An amount of items'})
        shpi_dir = (UTF8Block(length=4),
                    {'is_unknown': True,
                     'description': 'One of: "LN32", "GIMX", "WRAP". The purpose is unknown'})
        items_descr = (ArrayBlock(child=CompoundBlock(fields=[('name', UTF8Block(length=4), {}),
                                                              ('offset', IntegerBlock(length=4), {})],
                                                      inline_description='8-bytes record, first 4 bytes is a UTF-8 '
                                                                         'string, last 4 bytes is an unsigned integer '
                                                                         '(little-endian)'),
                                  length=lambda ctx: ctx.data('num_items')),
                       {'usage': 'io,doc',
                        'description': 'An array of items, each of them represents name of SHPI item (image or palette)'
                                       ' and offset to item data in file, relatively to SHPI block start (where '
                                       'resource id string is presented). Names are not always unique'})
        data_bytes = (BytesBlock(length=lambda ctx: determine_shpi_length(ctx)),
                      {
                          'usage': 'io,doc',
                          'description': 'A part of block, where items data is located. Offsets to some of the entries are '
                                         'defined in `items_descr` block. Between them there can be non-indexed '
                                         'entries (palettes and texts). Possible item types:'
                                         '<br/>- [EacImage](#eacimage)'
                                         '<br/>- [EacPalette](#eacpalette)'
                                         '<br/>- [PaletteReference](#palettereference)'
                                         '<br/>- [ShpiText](#shpitext)'})
        children = (ArrayBlock(child=None, length=None), {'usage': 'ui'})

    def new_data(self, patch=None):
        return {**super().new_data(), 'shpi_dir': 'LN32'}

    def estimate_packed_size(self, data, ctx: WriteContext = None):
        total_length = 16
        for i, child in enumerate(data['children']):
            total_length += len(child['pre_offset_payload']) + len(child['post_offset_payload'])
            total_length += self.item_block.estimate_packed_size(data=child['item'], ctx=ctx)
            if child['alias'] is not None:
                total_length += 8
        return total_length

    def read(self, ctx: ReadContext, name: str = '', read_bytes_amount=None):
        block_start = ctx.buffer.tell()
        res = super().read(ctx, name, read_bytes_amount)
        end_pos = ctx.buffer.tell()
        ctx.buffer.seek(-len(res['data_bytes']), SEEK_CUR)
        res['children'] = []

        abs_offsets = [
            (i, x['name'], block_start + x['offset'], None)
            for i, x in sorted(list(enumerate(res['items_descr'])), key=lambda x: x[1]['offset'])
        ]
        self_ctx = ctx.get_or_create_child(name, self, read_bytes_amount, res)
        try:
            bytes_choice = self.item_block.get_choice_index_by_class_name('BytesBlock')
        except StopIteration:
            bytes_choice = -1
        children_map = [None] * len(abs_offsets)
        for i, (descr_index, alias, offset, length) in enumerate(abs_offsets):
            child = {'item': None, 'alias': alias, 'pre_offset_payload': b'', 'post_offset_payload': b''}
            children_map[descr_index] = [child]
            if offset > ctx.buffer.tell():
                child['pre_offset_payload'] = ctx.buffer.read(offset - ctx.buffer.tell())
            else:
                ctx.buffer.seek(offset)
            try:
                child['item'] = self.item_block.unpack(ctx=self_ctx, name=f"{descr_index}_{alias}",
                                                       read_bytes_amount=length)
            except Exception:
                traceback.print_exc()
                ctx.buffer.seek(offset)
                child['item'] = {'choice_index': bytes_choice, 'data': ctx.buffer.read(length)}
            # Try to read optional extra block after 8-bit bitmap data
            if self_ctx.data('shpi_dir') != 'WRAP' and isinstance(child['item']['data'], dict) and child['item'][
                'data'].get(
                'resource_id') == '8Bit':
                extra_abs = offset + child['item']['data']['block_size']
                next_abs = abs_offsets[i + 1][2] if i < len(abs_offsets) - 1 else None
                if child['item']['data']['block_size'] > 0 and (next_abs is None or extra_abs < next_abs):
                    extra_child = {'item': None, 'alias': None, 'pre_offset_payload': b'', 'post_offset_payload': b''}
                    children_map[descr_index].append(extra_child)
                    if extra_abs > ctx.buffer.tell():
                        extra_child['pre_offset_payload'] = ctx.buffer.read(extra_abs - ctx.buffer.tell())
                    else:
                        ctx.buffer.seek(extra_abs)
                    extra_child['item'] = self.item_block.unpack(ctx=self_ctx, name=f'extra_{descr_index}')
        if res.get('length') is not None and ctx.buffer.tell() < block_start + res['length']:
            diff = block_start + res['length'] - ctx.buffer.tell()
            children_map[abs_offsets[-1][0]][-1]['post_offset_payload'] = ctx.buffer.read(diff)
        res['children'] = []
        for cs in children_map:
            res['children'].extend(cs)
        ctx.buffer.seek(end_pos)
        del res['items_descr']
        del res['data_bytes']
        return res

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        data['data_bytes'] = b''
        children = []
        for i, child in enumerate(data['children']):
            data['data_bytes'] += child['pre_offset_payload']
            item_data = self.item_block.pack(data=child['item'], ctx=ctx, name=str(i))
            children.append((child['alias'], len(data['data_bytes']), len(item_data)))
            data['data_bytes'] += item_data
            data['data_bytes'] += child['post_offset_payload']
        data['items_descr'] = [{'name': name, 'offset': offset} for (name, offset, _) in children if name is not None]
        heap_offset = 16 + len(data['items_descr']) * 8
        for x in data['items_descr']:
            x['offset'] += heap_offset
        ret = super().write(data=data, ctx=ctx, name=name)
        del data['items_descr']
        del data['data_bytes']
        return ret

    def action_convert_to_8bit(self, read_data, name, palette_name, palette_type, num_colors, id, **kwargs):
        # notes for future:

        # TNFS CFM files: last 6 colors are special for cars:
        # palette name is '!PAL'
        # 250th, 251th - cop red blinker
        # 252th, 253th - cop blue blinker
        # 254th is replaced with tail colors in the game
        # 255th is transparent
        # Also CFM has additional !xxx palette

        # TNFS FAM files:
        # palette name is '!PAL'

        import tempfile
        tmp_dir = tempfile.TemporaryDirectory()
        serializer = self.serializer_class()()
        serializer.patch_settings({'images__save_images_only': True})
        serializer.serialize(data=read_data, path=tmp_dir.name, block=self, id=name)

        bitmap_choice_index = self.item_block.get_choice_index_by_class_name('EacImage')
        read_data['children'] = [x for x in read_data['children'] if x['item']['choice_index'] == bitmap_choice_index]

        from library.utils import path_join
        from PIL import Image
        images = [Image.open(path_join(tmp_dir.name, x['alias'] + '.png')) for x in read_data['children']]

        max_width = max(img.width for img in images)
        total_height = sum(img.height for img in images)
        master_image = Image.new("RGB", (max_width, total_height), (0, 0, 0))
        current_y = 0
        contain_transparency = False
        for img in images:
            rgb = Image.new("RGB", img.size, (0, 0, 0))
            rgb.paste(img.convert("RGB"), mask=img.getchannel("A"))
            master_image.paste(rgb, (0, current_y))
            current_y += img.height
            if not contain_transparency:
                contain_transparency = img.getextrema()[3][0] < 255

        reserved_colors = 0
        if contain_transparency:
            reserved_colors += 1

        reference_palette_img = master_image.quantize(
            colors=256 - reserved_colors,
            method=Image.Quantize.FASTOCTREE
        )
        rgba_palette_data = reference_palette_img.getpalette("RGBA")[:(num_colors - reserved_colors) * 4]
        if contain_transparency:
            rgba_palette_data += [0, 255, 0, 0]
        rgb_palette_data = []
        for i in range(0, len(rgba_palette_data), 4):
            rgb_palette_data.extend(rgba_palette_data[i:i + 3])
        dummy_palette_img = Image.new("P", (1, 1))
        dummy_palette_img.putpalette(rgb_palette_data, "RGB")
        for child, img in zip(read_data['children'], images):
            alpha = img.getchannel("A")
            rgb = Image.new("RGB", img.size, (0, 0, 0))
            rgb.paste(img.convert("RGB"), mask=alpha)
            q_img = rgb.quantize(palette=dummy_palette_img)
            data = bytearray(q_img.tobytes())
            if contain_transparency:
                alpha_data = alpha.load()
                w, h = img.size
                k = 0
                for y in range(h):
                    for x in range(w):
                        if alpha_data[x, y] == 0:
                            data[k] = 255
                        k += 1

            q_img = Image.frombytes("P", img.size, bytes(data))
            q_img.putpalette(rgba_palette_data, "RGBA")
            child['item']['data']['resource_id'] = '8Bit'
            child['item']['data']['bitmap'] = list(q_img.getdata())
        pal = EacPalette().new_data()
        pal['resource_id'] = '32Bit color format palette'
        pal['colors']['data'] = [
            (rgba_palette_data[i] << 24)
            | (rgba_palette_data[i + 1] << 16)
            | (rgba_palette_data[i + 2] << 8)
            | rgba_palette_data[i + 3]
            for i in range(0, len(rgba_palette_data), 4)
        ]
        read_data['children'].insert(0, {
            'pre_offset_payload': b'',
            'post_offset_payload': b'',
            'alias': palette_name,
            'item': {
                'choice_index': self.item_block.get_choice_index_by_class_name('EacPalette'),
                'data': pal
            }
        })
        if palette_type != '32Bit color format palette':
            EacPalette().action_convert_format(pal, palette_type, id=join_id(id, 'children', '0', 'item', 'data'))

    def serializer_class(self):
        from serializers import ShpiArchiveSerializer
        return ShpiArchiveSerializer
