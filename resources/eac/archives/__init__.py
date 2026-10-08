from copy import deepcopy
from typing import Dict

from library.context import ReadContext, WriteContext
from library.read_blocks import (
    DeclarativeCompoundBlock,
    UTF8Block,
    IntegerBlock,
    ArrayBlock,
    AutoDetectBlock,
    BytesBlock,
)
from library.read_blocks.archives import ArchiveBlock, read_gap, slot_lengths
from library.read_blocks.misc.value_validators import Eq
from library.read_blocks.strings import NullTerminatedUTF8Block
from resources.eac.audios import EacsAudioFile, SoundBankHeaderEntry
from resources.common.bitmaps.targa_image import TargaImage
from .shpi_block import ShpiBlock
from .compressed_block import EacCompressedBlock


class WwwwBlock(ArchiveBlock):
    @property
    def schema(self) -> Dict:
        # this schema has recursion problem. Workaround applied here
        if getattr(self, 'schema_call_recv', False):
            return {
                'block_class_mro': '__'.join(
                    [x.__name__ for x in self.__class__.mro() if x.__name__ not in ['object', 'ABC']]
                ),
                'is_recursive_ref': True,
            }
        self.schema_call_recv = True
        schema = {
            **super().schema,
            'block_description': 'A block-container with various data: image archives, geometries, other wwww blocks. '
            'If has ORIP 3D model, next item is always SHPI block with textures to this 3D model',
        }
        delattr(self, 'schema_call_recv')
        return schema

    def __init__(self, **kwargs):
        from resources.eac.geometries import OripGeometry

        super().__init__(
            item_block=AutoDetectBlock(
                possible_blocks=[
                    ShpiBlock(),
                    OripGeometry(),
                    self,
                    BytesBlock(
                        length=(
                            lambda ctx: next(
                                x
                                for x in (
                                    x - ctx.local_buffer_pos
                                    for x in (sorted(ctx.data('items_descr')) + [ctx.read_bytes_amount])
                                )
                                if x > 0
                            ),
                            'item_length',
                        )
                    ),
                ]
            ),
            **kwargs,
        )

    class Fields(ArchiveBlock.Fields):
        resource_id = (UTF8Block(value_validator=Eq('wwww'), length=4), {'description': 'Resource ID'})
        num_items = (
            IntegerBlock(length=4, programmatic_value=lambda ctx: len(ctx.data('items_descr'))),
            {'description': 'An amount of items'},
        )
        items_descr = (
            ArrayBlock(child=IntegerBlock(length=4), length=lambda ctx: ctx.data('num_items')),
            {
                'usage': 'io,doc',
                'description': 'An array of offsets to items data in file, relatively to wwww block start '
                '(where resource id string is presented)',
            },
        )
        data_bytes = (
            BytesBlock(length=lambda ctx: ctx.read_bytes_remaining),
            {
                'usage': 'io,doc',
                'description': 'A part of block, where items data is located. Offsets are defined in previous '
                'block, lengths are calculated: either up to next item offset, or up to the end '
                'of this block. Possible item types:'
                '<br/>- [ShpiBlock](#shpiblock)'
                '<br/>- [OripGeometry](#oripgeometry)'
                '<br/>- [WwwwBlock](#wwwwblock)',
            },
        )
        children = (ArrayBlock(child=None, length=None), {'usage': 'ui'})

    def estimate_packed_size(self, data, ctx: WriteContext = None):
        total_length = 8
        for i, child in enumerate(data['children']):
            total_length += sum(self.entry_sizes(child, ctx))
            total_length += 4
        return total_length

    def read(self, ctx: ReadContext, name: str = '', read_bytes_amount=None):
        block_start = ctx.buffer.tell()
        res, self_ctx, region_start, region_length = self.read_header(ctx, name, read_bytes_amount)
        end_pos = region_start + region_length

        offsets = [block_start + x for x in res['items_descr']]
        items = [(i, offset) for i, offset in enumerate(offsets) if offset != block_start]
        lengths = slot_lengths([offset for _, offset in items], end_pos)
        first_offset = min((offset for _, offset in items), default=None)
        # entries are parsed later in lazy mode: keep header (with io-only fields) for their contexts
        entry_ctx = self_ctx.detached(ctx.buffer, data=dict(res)) if self_ctx.lazy else self_ctx
        # self-reference, ignore
        children = [
            {
                'item': {'choice_index': self.bytes_choice, 'data': b''},
                'pre_offset_payload': b'',
                'post_offset_payload': b'',
            }
            for _ in offsets
        ]
        for (i, offset), length in zip(items, lengths):
            children[i] = self.read_entry(
                entry_ctx,
                name=str(i),
                offset=offset,
                length=length,
                pre_offset_payload=read_gap(ctx, region_start, offset) if offset == first_offset else b'',
            )
        res['children'] = children
        ctx.buffer.seek(end_pos)
        del res['items_descr']
        return res

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        data['data_bytes'] = b''
        data['items_descr'] = []
        for i, child in enumerate(data['children']):
            pre, item_data, post = self.entry_bytes(child, ctx, str(i))
            data['data_bytes'] += pre
            data['items_descr'].append(len(data['data_bytes']))
            data['data_bytes'] += item_data
            data['data_bytes'] += post
        heap_offset = 8 + len(data['items_descr']) * 4
        data['items_descr'] = [x + heap_offset for x in data['items_descr']]
        ret = super().write(data=data, ctx=ctx, name=name)
        del data['items_descr']
        del data['data_bytes']
        return ret

    def serializer_class(self):
        from serializers import WwwwArchiveSerializer

        return WwwwArchiveSerializer


class BigfItemDescriptionBlock(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {**super().schema, 'block_description': 'Description of a single item of BIGF archive'}

    class Fields(DeclarativeCompoundBlock.Fields):
        offset = (
            IntegerBlock(length=4, byte_order='big'),
            {'description': 'Offset of item data, relative to BIGF block start'},
        )
        length = (IntegerBlock(length=4, byte_order='big'), {'description': 'Length of item data in bytes'})
        name = (
            NullTerminatedUTF8Block(length=8),
            {'description': 'Item name (file name). Used as file name when the archive is unpacked'},
        )


class BigfBlock(ArchiveBlock):
    @property
    def schema(self) -> Dict:
        # this schema has recursion problem. Workaround applied here
        if getattr(self, 'schema_call_recv', False):
            return {
                'block_class_mro': '__'.join(
                    [x.__name__ for x in self.__class__.mro() if x.__name__ not in ['object', 'ABC']]
                ),
                'is_recursive_ref': True,
            }
        self.schema_call_recv = True
        schema = {
            **super().schema,
            'block_description': 'A block-container with various data: image archives, GEO geometries, sound banks, '
            'other BIGF blocks...',
        }
        delattr(self, 'schema_call_recv')
        return schema

    def __init__(self, **kwargs):
        from resources.eac.geometries import GeoGeometry, Fce3Geometry, Fce4Geometry, EaglModel

        super().__init__(
            item_block=AutoDetectBlock(
                possible_blocks=[
                    GeoGeometry(),
                    Fce3Geometry(),
                    Fce4Geometry(),
                    EaglModel(),
                    ShpiBlock(),
                    EacCompressedBlock(),
                    TargaImage(),
                    self,
                    BytesBlock(
                        length=(
                            lambda ctx: next(x for x in ctx.data('items_descr') if x['offset'] == ctx.local_buffer_pos)[
                                'length'
                            ],
                            'item_length',
                        )
                    ),
                ]
            ),
            alias_field=NullTerminatedUTF8Block(length=8),
            **kwargs,
        )

    class Fields(ArchiveBlock.Fields):
        resource_id = (UTF8Block(length=4, value_validator=Eq('BIGF')), {'description': 'Resource ID'})
        length = (
            IntegerBlock(
                length=4,
                byte_order='big',
                programmatic_value=lambda ctx: ctx.block.length_field_value(ctx.get_full_data()),
            ),
            {
                'description': 'The length of this BIGF block in bytes. NFS6 stores the length without padding '
                'between items: header plus item lengths'
            },
        )
        num_items = (
            IntegerBlock(length=4, byte_order='big', programmatic_value=lambda ctx: len(ctx.data('items_descr'))),
            {'description': 'An amount of items'},
        )
        unk0 = (IntegerBlock(length=4), {'is_unknown': True})
        items_descr = (
            ArrayBlock(length=lambda ctx: ctx.data('num_items'), child=BigfItemDescriptionBlock()),
            {'usage': 'io,doc', 'description': 'Descriptions of items: offset, length and name of each of them'},
        )
        data_bytes = (
            BytesBlock(length=lambda ctx: ctx.read_bytes_remaining),
            {
                'usage': 'io,doc',
                'description': 'A part of block, where items data is located. Offsets and lengths are defined '
                'in previous block. Possible item types:'
                '<br/>- [GeoGeometry](#geogeometry)'
                '<br/>- [Fce3Geometry](#fce3geometry)'
                '<br/>- [Fce4Geometry](#fce4geometry)'
                '<br/>- [ShpiBlock](#shpiblock), can be compressed like QFS file'
                '<br/>- [BigfBlock](#bigfblock)'
                '<br/>- pure TGA image',
            },
        )
        children = (ArrayBlock(child=None, length=None), {'usage': 'ui'})

    def length_field_value(self, data) -> int:
        """Value of "length" header field: block size, or (NFS6) size without padding between items. The second
        one is used when the field read from file has it"""
        size = self.estimate_packed_size(data)
        unpadded = size - sum(pre + post for (pre, _, post) in (self.entry_sizes(c) for c in data['children']))
        return unpadded if data.get('length') == unpadded else size

    def estimate_packed_size(self, data, ctx: WriteContext = None):
        total_length = 16
        for i, child in enumerate(data['children']):
            total_length += sum(self.entry_sizes(child, ctx))
            total_length += 9 + len(child['alias'])
        return total_length

    def read(self, ctx: ReadContext, name: str = '', read_bytes_amount=None):
        block_start = ctx.buffer.tell()
        res, self_ctx, region_start, region_length = self.read_header(ctx, name, read_bytes_amount)
        end_pos = region_start + region_length

        entries = sorted(list(enumerate(res['items_descr'])), key=lambda x: x[1]['offset'])
        offsets = [block_start + x['offset'] for _, x in entries]
        lengths = []
        if entries:
            # the last item owns bytes up to the block length from the header (NFS6 has it without padding)
            last_item_end = offsets[-1] + entries[-1][1]['length']
            lengths = slot_lengths(offsets, min(end_pos, max(block_start + (res.get('length') or 0), last_item_end)))
        # entries are parsed later in lazy mode: keep header (with io-only fields) for their contexts
        entry_ctx = self_ctx.detached(ctx.buffer, data=dict(res)) if self_ctx.lazy else self_ctx
        children = [None] * len(entries)
        for i, ((descr_index, descr), offset, length) in enumerate(zip(entries, offsets, lengths)):
            children[descr_index] = self.read_entry(
                entry_ctx,
                name=f'{descr_index}_{descr["name"]}',
                offset=offset,
                length=length,
                item_length=descr['length'],
                alias=descr['name'],
                pre_offset_payload=read_gap(ctx, region_start, offset) if i == 0 else b'',
            )
        res['children'] = children
        ctx.buffer.seek(end_pos)
        del res['items_descr']
        return res

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        data['data_bytes'] = b''
        children = []
        for i, child in enumerate(data['children']):
            pre, item_data, post = self.entry_bytes(child, ctx, str(i))
            data['data_bytes'] += pre
            children.append((child['alias'], len(data['data_bytes']), len(item_data)))
            data['data_bytes'] += item_data
            data['data_bytes'] += post
        data['items_descr'] = [
            {'name': name, 'offset': offset, 'length': length}
            for (name, offset, length) in children
            if name is not None
        ]
        heap_offset = 16
        for x in data['items_descr']:
            heap_offset += 9 + len(x['name'])
        for x in data['items_descr']:
            x['offset'] += heap_offset
        ret = super().write(data=data, ctx=ctx, name=name)
        del data['items_descr']
        del data['data_bytes']
        return ret

    def serializer_class(self):
        from serializers import BigfArchiveSerializer

        return BigfArchiveSerializer


class SoundBank(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'A pack of SFX samples (short audios). Used mostly for car engine sounds, '
            'crash sounds etc.',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        items_descr = (
            ArrayBlock(child=IntegerBlock(length=4, is_signed=False), length=128),
            {'description': 'An array of offsets to items data in file. Zero values ignored'},
        )
        items = (
            ArrayBlock(
                child=SoundBankHeaderEntry(),
                length=(
                    lambda ctx: len([x for x in ctx.data('items_descr') if x > 0]),
                    'amount of non-zero elements in items_descr',
                ),
            ),
            {
                'description': 'EACS audio headers. Separate audios can be read easily using these because '
                'it contains file-wide offset to wave data, so it does not care wave data located, '
                'right after EACS header, or somewhere else like it is here in sound bank file'
            },
        )
        wave_data = (
            BytesBlock(length=lambda ctx: ctx.read_bytes_remaining),
            {
                'description': 'Raw byte data, which is sliced according to provided offsets and used as wave data',
                'usage': 'io,doc',
            },
        )
        children = (
            ArrayBlock(child=EacsAudioFile(), length=(0, 'amount of non-zero elements in items_descr')),
            {'description': 'EACS audios', 'usage': 'ui'},
        )

    def serializer_class(self):
        from serializers import SoundBankSerializer

        return SoundBankSerializer

    def read(self, ctx: ReadContext, name: str = '', read_bytes_amount=None):
        bnk_start = ctx.buffer.tell()
        res = super().read(ctx, name, read_bytes_amount)

        # EacsAudioFile will store offset bytes between header and wave data. We don't want it here because
        # *.BNK contains many headers first, and then has big sequence of wave data.
        # Let's build result object artificially
        global_wave_offset = bnk_start + self.offset_to_child_when_packed(res, 'wave_data')
        res['children'] = []
        res['children_offsets'] = []
        slices = []
        last_slice_end = 0
        for item in res['items']:
            offset = item['eacs_header']['wave_data_offset'] - global_wave_offset
            length = (
                item['eacs_header']['wave_data_length']
                * item['eacs_header']['sound_resolution']
                * item['eacs_header']['channels']
            )
            res['children_offsets'].append(res['wave_data'][last_slice_end:offset])
            last_slice_end = offset + length
            slices.append((offset, offset + length))
            res['children'].append(
                {'header': item['eacs_header'], 'offset': b'', 'wave_data': res['wave_data'][offset : offset + length]}
            )
        res['children_offsets'].append(res['wave_data'][last_slice_end:])
        res['wave_data'] = b''
        return res

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        wave_data_heap = b''
        wave_data_offset = self.offset_to_child_when_packed(data, 'wave_data')
        wave_pointers = []
        for i, child in enumerate(data['children']):
            wave_data_heap += data['children_offsets'][i]
            try:
                wave_pointers.append(wave_data_offset + wave_data_heap.index(child['wave_data']))
            except ValueError:
                wave_pointers.append(wave_data_offset + len(wave_data_heap))
                wave_data_heap += child['wave_data']
        wave_data_heap += data['children_offsets'][-1]
        for i, item in enumerate(data['items']):
            item['eacs_header']['wave_data_offset'] = wave_pointers[i]
        data_to_write = deepcopy(data)
        data_to_write['wave_data'] = wave_data_heap
        data_to_write['children'] = []
        return super().write(data_to_write, ctx, name)
