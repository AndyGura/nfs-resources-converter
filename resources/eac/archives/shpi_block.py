import traceback
from io import SEEK_CUR
from typing import Dict

from config import general_config
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
from resources.eac.bitmaps import EacImage, EacPalette
from resources.eac.misc import ShpiText
from .base_archive_block import BaseArchiveBlock


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
        return {
            **super().schema,
            'block_description': 'A container of images and palettes for them',
        }

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
            ) if x > 0), 'item_length'))]), **kwargs)

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

    def new_data(self):
        return {**super().new_data(), 'shpi_dir': 'LN32'}

    def read(self, ctx: ReadContext, name: str = '', read_bytes_amount=None):
        block_start = ctx.buffer.tell()
        res = super().read(ctx, name, read_bytes_amount)
        end_pos = ctx.buffer.tell()
        ctx.buffer.seek(-len(res['data_bytes']), SEEK_CUR)
        res['children'] = []

        abs_offsets = [(x['name'], block_start + x['offset'], None) for x in res['items_descr']]
        self_ctx = ctx.get_or_create_child(name, self, read_bytes_amount, res)
        try:
            bytes_choice = next(idx
                                for idx, blk in enumerate(self.item_block.possible_blocks)
                                if isinstance(blk, BytesBlock))
        except StopIteration:
            bytes_choice = -1
        for i, (alias, offset, length) in enumerate(abs_offsets):
            child = { 'item': None, 'alias': alias, 'pre_offset_payload': b'', 'post_offset_payload': b'' }
            res['children'].append(child)
            if offset > ctx.buffer.tell():
                child['pre_offset_payload'] = ctx.buffer.read(offset - ctx.buffer.tell())
            else:
                ctx.buffer.seek(offset)
            try:
                child['item'] = self.item_block.unpack(ctx=self_ctx, name=f"{i}_{alias}", read_bytes_amount=length)
            except Exception:
                if general_config().print_errors:
                    traceback.print_exc()
                ctx.buffer.seek(offset)
                child['item'] = {'choice_index': bytes_choice, 'data': ctx.buffer.read(length)}
            # Try to read optional extra block after 8-bit bitmap data
            if self_ctx.data('shpi_dir') != 'WRAP' and isinstance(child['item']['data'], dict) and child['item']['data'].get(
                    'resource_id') == '8Bit':
                extra_abs = offset + child['item']['data']['block_size']
                next_abs = abs_offsets[i + 1][1] if i < len(abs_offsets) - 1 else None
                if child['item']['data']['block_size'] > 0 and (next_abs is None or extra_abs < next_abs):
                    extra_child = { 'item': None, 'alias': None, 'pre_offset_payload': b'', 'post_offset_payload': b'' }
                    res['children'].append(extra_child)
                    if extra_abs > ctx.buffer.tell():
                        extra_child['pre_offset_payload'] = ctx.buffer.read(extra_abs - ctx.buffer.tell())
                    else:
                        ctx.buffer.seek(extra_abs)
                    extra_child['item'] = self.item_block.unpack(ctx=self_ctx, name=f'extra_{i}')
        if res.get('length') is not None and ctx.buffer.tell() < block_start + res['length']:
            diff = block_start + res['length'] - ctx.buffer.tell()
            res['children'][-1]['post_offset_payload'] = ctx.buffer.read(diff)
        ctx.buffer.seek(end_pos)
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
        heap_offset = self.offset_to_child_when_packed({**data, 'items_descr': data['items_descr']}, 'data_bytes')
        for x in data['items_descr']:
            x['offset'] += heap_offset
        return super().write(data=data, ctx=ctx, name=name)

    def serializer_class(self):
        from serializers import ShpiArchiveSerializer
        return ShpiArchiveSerializer
