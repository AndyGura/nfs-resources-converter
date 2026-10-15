from copy import deepcopy
from typing import Dict, List

from library.context import ReadContext, WriteContext
from library.read_blocks import (
    DeclarativeCompoundBlock,
    UTF8Block,
    IntegerBlock,
    ArrayBlock,
    AutoDetectBlock,
    BytesBlock,
    OptionalBlock,
)
from library.read_blocks.archives import ArchiveBlock, pre_items_payload_length, slot_lengths
from library.read_blocks.misc.value_validators import Eq
from library.read_blocks.strings import NullTerminatedUTF8Block
from resources.eac.audios import EacsAudioFile, SoundBankHeaderEntry, EaSoundPatch
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
        pre_items_payload = (
            BytesBlock(
                length=(
                    lambda ctx: pre_items_payload_length(ctx, [x for x in ctx.data('items_descr') if x > 0]),
                    'up to the first item offset',
                )
            ),
            {
                'description': 'Bytes between the end of `items_descr` and the first item: padding, or data which '
                'no item offset points to',
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

    def entry_kind_hint(self, head: bytes):
        return {b'SHPI': 'ShpiBlock', b'ORIP': 'OripGeometry', b'wwww': 'WwwwBlock'}.get(head[:4], 'BytesBlock')

    def estimate_packed_size(self, data, ctx: WriteContext = None):
        total_length = 8 + len(data.get('pre_items_payload', b''))
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
        # entries are parsed later in lazy mode: keep header (with io-only fields) for their contexts
        entry_ctx = self_ctx.detached(ctx.buffer, data=dict(res)) if self_ctx.lazy else self_ctx
        # self-reference, ignore
        children = [
            {'item': {'choice_index': self.bytes_choice, 'data': b''}, 'post_offset_payload': b''} for _ in offsets
        ]
        for (i, offset), length in zip(items, lengths):
            children[i] = self.read_entry(entry_ctx, name=str(i), offset=offset, length=length)
        res['children'] = children
        ctx.buffer.seek(end_pos)
        del res['items_descr']
        return res

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        data['data_bytes'] = b''
        data['items_descr'] = []
        for i, child in enumerate(data['children']):
            if self._is_empty_entry(child):
                # offset 0: an entry without data, as the files mark it (read as empty bytes)
                data['items_descr'].append(None)
                continue
            item_data, post = self.entry_bytes(child, ctx, str(i))
            data['items_descr'].append(len(data['data_bytes']))
            data['data_bytes'] += item_data
            data['data_bytes'] += post
        heap_offset = 8 + len(data['items_descr']) * 4 + len(data.get('pre_items_payload', b''))
        data['items_descr'] = [0 if x is None else x + heap_offset for x in data['items_descr']]
        ret = super().write(data=data, ctx=ctx, name=name)
        del data['items_descr']
        del data['data_bytes']
        return ret

    def _is_empty_entry(self, child) -> bool:
        from library.lazy import LazyDict

        if isinstance(child, LazyDict) and not child.is_loaded:
            # unloaded entries are read from an offset
            return False
        item = child['item']
        return (
            item is not None
            and item['choice_index'] == self.bytes_choice
            and len(item['data']) == 0
            and len(child['post_offset_payload']) == 0
        )

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
                    EaSoundBank(),
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
        pre_items_payload = (
            BytesBlock(
                length=(
                    lambda ctx: pre_items_payload_length(ctx, [x['offset'] for x in ctx.data('items_descr')]),
                    'up to the first item offset',
                )
            ),
            {
                'description': 'Bytes between the end of `items_descr` and the first item: padding, or data which '
                'no item offset points to',
            },
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
                '<br/>- [EaSoundBank](#easoundbank)'
                '<br/>- pure TGA image',
            },
        )
        children = (ArrayBlock(child=None, length=None), {'usage': 'ui'})

    def length_field_value(self, data) -> int:
        """Value of "length" header field: block size, or (NFS6) size without padding between items. The second
        one is used when the field read from file has it"""
        size = self.estimate_packed_size(data)
        padding = len(data.get('pre_items_payload', b'')) + sum(
            post for (_, post) in map(self.entry_sizes, data['children'])
        )
        unpadded = size - padding
        return unpadded if data.get('length') == unpadded else size

    def estimate_packed_size(self, data, ctx: WriteContext = None):
        total_length = 16 + len(data.get('pre_items_payload', b''))
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
            )
        res['children'] = children
        ctx.buffer.seek(end_pos)
        del res['items_descr']
        return res

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        data['data_bytes'] = b''
        children = []
        for i, child in enumerate(data['children']):
            item_data, post = self.entry_bytes(child, ctx, str(i))
            children.append((child['alias'], len(data['data_bytes']), len(item_data)))
            data['data_bytes'] += item_data
            data['data_bytes'] += post
        data['items_descr'] = [
            {'name': name, 'offset': offset, 'length': length}
            for (name, offset, length) in children
            if name is not None
        ]
        heap_offset = 16 + len(data.get('pre_items_payload', b''))
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
            'crash sounds etc. In TNFS all banks of a race share one 128-entry sample id table: the game loads the '
            'car bank, the opponent banks, the collision bank (`COLL*`), then `NFS_FMMB`, and a bank loaded later '
            'replaces the ids it has',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        items_descr = (
            ArrayBlock(child=IntegerBlock(length=4, is_signed=False), length=128),
            {
                'description': 'Offsets of `items` in the file, the array index being the sample index used by the '
                'game. Zero values ignored. Entries are not always stored in index order (in TNFS collision banks '
                'entry 0x50 precedes 0x3d-0x40)'
            },
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
                'description': 'Sound bank entries in file order (see `items_descr` for their indices). '
                'EACS audio headers in them can be read easily because '
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

    @staticmethod
    def item_indices(data: dict) -> List[int]:
        """`items_descr` index of every entry of `items` / `children`, which are in file order, not index order"""
        used = [(i, offset) for (i, offset) in enumerate(data['items_descr']) if offset > 0]
        return [i for (i, _) in sorted(used, key=lambda x: x[1])]

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
        # bytes between the end of the wave data seen so far and the next one. Entries can share wave data (several
        # indices for one wav in collision banks): such an entry points back into the data already seen, gets an empty
        # gap and is found again by `write`, which reuses identical wave data
        last_slice_end = 0
        for item in res['items']:
            offset = item['eacs_header']['wave_data_offset'] - global_wave_offset
            length = (
                item['eacs_header']['wave_data_length']
                * item['eacs_header']['sound_resolution']
                * item['eacs_header']['channels']
            )
            res['children_offsets'].append(res['wave_data'][last_slice_end:offset])
            last_slice_end = max(last_slice_end, offset + length)
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


class EaSoundBank(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'EA sound bank "BNKl" (*.BNK of NFS2, NFS2 SE, NFS3, NFS4, NFS5, NFS6): a table of '
            'sound patches, then their wave data. Car banks (NFS2 `<car>.BNK` / `O<car>.BNK` (opponent) / '
            '`S<car>.BNK`, NFS3 `car.bnk` / `ocar.bnk` / `scar.bnk` in car.viv, NFS4 `careng.bnk` / `ocareng.bnk` / '
            '`scareng.bnk`, NFS3/NFS4 `GENCAR.BNK`, traffic `TRUCK.BNK`...) use indices 0 and 1 for the engine '
            '(looped), 2 for a one-shot with random detune range 200-250 (gear shift, like `gear` of TNFS car banks) '
            'and 3 for the horn (looped). Opponent banks have the engine and the horn only: NFS2 `O<car>.BNK` in '
            'slots 0 and 1 of a 2-slot table, NFS3 `ocar.bnk` / NFS4 `ocareng.bnk` in slots 0 and 3. NFS4 '
            '`careng.bnk` has more engine samples at higher indices (presumably one per RPM range). `W*.BNK` of NFS2 '
            'SE are car speech',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (UTF8Block(length=4, value_validator=Eq('BNKl')), {'description': 'Resource ID'})
        version = (
            IntegerBlock(length=2),
            {
                'description': '2 (NFS2, NFS2 SE, most of NFS3 GameData/Audio/SFX), 4 (NFS3 car.viv, NFS4, NFS5, NFS6) or 5 (NFS6)'
            },
        )
        num_items = (
            IntegerBlock(length=2, programmatic_value=lambda ctx: len(ctx.data('items_descr'))),
            {'description': 'Amount of slots in `items_descr`'},
        )
        header_length = (
            IntegerBlock(length=4),
            {
                'description': 'Version 2 and 4: offset of the wave data, i.e. the length of the table and the '
                'patches. Version 5: file length'
            },
        )
        wave_data_length = (
            OptionalBlock(
                IntegerBlock(length=4), criteria=(lambda ctx: ctx.data('version') >= 4, 'version >= 4'), default_value=0
            ),
            {'description': 'Version 4: length of the wave data. Version 5: 0'},
        )
        unk0 = (
            OptionalBlock(
                IntegerBlock(length=4), criteria=(lambda ctx: ctx.data('version') >= 4, 'version >= 4'), default_value=0
            ),
            {'is_unknown': True},
        )
        items_descr = (
            ArrayBlock(child=IntegerBlock(length=4), length=lambda ctx: ctx.data('num_items')),
            {
                'description': 'Offset of every patch, relative to its own position in this table, the array index '
                'being the sample index used by the game. 0 is an empty slot'
            },
        )
        data_bytes = (
            BytesBlock(length=lambda ctx: ctx.read_bytes_remaining),
            {
                'description': 'Sound patches ([EaSoundPatch](#easoundpatch)) at the offsets of `items_descr`, then '
                'wave data',
                'usage': 'io,doc',
            },
        )
        items = (
            ArrayBlock(child=EaSoundPatch(), length=(0, 'amount of non-zero elements in items_descr')),
            {
                'description': 'Sound patches of non-empty slots, in table order. Their tags are written back in '
                'place: a value can change, the length of a value can not',
                'usage': 'ui',
            },
        )

    def _table_offset(self, data) -> int:
        return 20 if data['version'] >= 4 else 12

    def item_indices(self, data) -> List[int]:
        """`items_descr` index of every entry of `items`"""
        return [i for (i, x) in enumerate(data['items_descr']) if x > 0]

    def _patch_positions(self, data) -> List[int]:
        """Position of every patch of `items` in `data_bytes`"""
        table_offset = self._table_offset(data)
        data_bytes_offset = table_offset + 4 * len(data['items_descr'])
        return [table_offset + 4 * i + data['items_descr'][i] - data_bytes_offset for i in self.item_indices(data)]

    def wave_data(self, data, layer: Dict) -> bytes:
        """Wave data of a layer (see `EaSoundPatch.layers`), from the bank's data bytes; `layer['data_offset']` is
        relative to the start of the bank"""
        offset = layer['data_offset'] - self._table_offset(data) - 4 * len(data['items_descr'])
        return data['data_bytes'][offset:]

    def read(self, ctx: ReadContext, name: str = '', read_bytes_amount=None):
        res = super().read(ctx, name, read_bytes_amount)
        patch_block = self.field_blocks_map['items'].child
        res['items'] = [
            patch_block.unpack_from_bytes(res['data_bytes'][pos:], name=f'items/{i}')
            for (i, pos) in enumerate(self._patch_positions(res))
        ]
        return res

    def _native_data(self, data):
        data = deepcopy(data)
        patch_block = self.field_blocks_map['items'].child
        data_bytes = bytearray(data['data_bytes'])
        for pos, item in zip(self._patch_positions(data), data['items']):
            packed = patch_block.pack(item)
            original_length = patch_block.estimate_packed_size(patch_block.unpack_from_bytes(data['data_bytes'][pos:]))
            if len(packed) != original_length:
                raise ValueError('Cannot change the length of a sound patch tag value')
            data_bytes[pos : pos + len(packed)] = packed
        data['data_bytes'] = bytes(data_bytes)
        data['items'] = []
        return data

    def estimate_packed_size(self, data, ctx: WriteContext = None):
        return self._table_offset(data) + 4 * len(data['items_descr']) + len(data['data_bytes'])

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        return super().write(self._native_data(data), ctx, name)

    def serializer_class(self):
        from serializers import EaSoundBankSerializer

        return EaSoundBankSerializer
