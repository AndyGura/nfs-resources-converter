import traceback
from abc import ABC
from typing import List, Optional, Tuple

from library.context import ReadContext, WriteContext
from library.lazy import LazyDict, Slot, source_for_buffer, unloaded_slot
from library.read_blocks import CompoundBlock, DeclarativeCompoundBlock, BytesBlock


# Base abstract class for archive blocks
# Subclasses should:
# 1) Provide item block to super().__init__
# 2) Declare own compound block fields as usual, documentation and io friendly
# 3) Declare fields like children offsets, children array etc. usage to be "io,doc" (skip showing in UI)
# 4) Add `children = (ArrayBlock(child=None, length=None), {'usage': 'ui'})` to Fields class
# 5) Update read function to produce "children" array as per structure, implemented here: `read_header` reads
#    everything but the items region (`data_bytes` field, must be the last io field), `read_entry` reads one item
# 6) Update write function to use "children" array as per structure, and transform it to the io format, getting
#    bytes of each entry with `entry_bytes`
# 7) Override estimate_packed_size (look at shpi example), sizing entries with `entry_sizes`
#
# Entry bytes: an entry owns its slot, from its item offset up to the offset of the next item (in the file order).
# The item is parsed from the slot start, bytes left after the item end are `post_offset_payload`. Bytes between the
# items region start and the first item are `pre_offset_payload` of the first item.
# With lazy read context, entries are unloaded `LazyDict`s, seeded with `alias` and `pre_offset_payload`. Unloaded
# entry is written back as its original slot bytes.
class ArchiveBlock(DeclarativeCompoundBlock, ABC):
    def __init__(self, item_block, alias_field=None, **kwargs):
        super().__init__(**kwargs)
        self.item_block = item_block
        fields = [
            ('item', item_block, {}),
            ('pre_offset_payload', BytesBlock(length=None), {}),
            ('post_offset_payload', BytesBlock(length=None), {}),
        ]
        if alias_field is not None:
            fields.append(('alias', alias_field, {}))
        self.has_alias = alias_field is not None
        self.entry_keys = frozenset(name for (name, _, _) in fields)
        self.field_blocks_map['children'].child = CompoundBlock(fields=fields)

    @property
    def bytes_choice(self) -> int:
        try:
            return self.item_block.get_choice_index_by_class_name('BytesBlock')
        except ValueError:
            return -1

    def read_header(
        self, ctx: ReadContext, name: str = '', read_bytes_amount=None
    ) -> Tuple[dict, ReadContext, int, int]:
        """Reads io fields before `data_bytes`. Returns data, own context, absolute start and length of items region.
        Buffer is left at the region start"""
        res = dict()
        self_ctx = ctx.get_or_create_child(name, self, read_bytes_amount, res)
        region_start, region_length = None, 0
        for field_name, field in self.field_blocks:
            usage = self.field_extras_map.get(field_name, {}).get('usage', 'everywhere')
            if usage != 'everywhere' and 'io' not in usage:
                continue
            if field_name == 'data_bytes':
                region_start = ctx.buffer.tell()
                region_length = field.resolve_length(self_ctx)
                break
            res[field_name] = field.unpack(
                ctx=self_ctx, name=field_name, read_bytes_amount=self_ctx.read_bytes_remaining
            )
        return res, self_ctx, region_start, region_length

    def read_entry(
        self,
        ctx: ReadContext,
        name: str,
        offset: int,
        length: int,
        item_length: Optional[int] = None,
        alias=None,
        pre_offset_payload: bytes = b'',
    ):
        """One entry (`children` item). `offset` and `length` are the absolute slot, the item is read with
        `read_bytes_amount=item_length` (whole slot by default). `ctx` should hold the header data, including io-only
        fields, for item blocks looking them up. Returns a plain dict, or an unloaded `LazyDict` if ctx is lazy"""
        seed = {}
        if self.has_alias:
            seed['alias'] = alias
        seed['pre_offset_payload'] = pre_offset_payload
        slot = Slot(
            source=None,
            offset=offset,
            length=max(0, length),
            item_length=length if item_length is None else item_length,
            parse_fn=_parse_entry,
            parent_ctx=ctx,
            keys=self.entry_keys,
            seed=seed,
            args=(self, name),
        )
        if ctx.lazy:
            slot.source = source_for_buffer(ctx.buffer)
            if slot.source is not None:
                return LazyDict(slot)
        ctx.buffer.seek(offset)
        return _parse_entry(ctx, slot)

    def entry_sizes(self, child, ctx: WriteContext = None) -> Tuple[int, int, int]:
        """Lengths of pre-offset payload, item and post-offset payload of entry when packed"""
        slot = unloaded_slot(child)
        if slot is not None:
            item_length = min(slot.item_length, slot.length)
            return len(dict.__getitem__(child, 'pre_offset_payload')), item_length, slot.length - item_length
        return (
            len(child['pre_offset_payload']),
            self.item_block.estimate_packed_size(data=child['item'], ctx=ctx),
            len(child['post_offset_payload']),
        )

    def entry_bytes(self, child, ctx: WriteContext = None, name: str = '') -> Tuple[bytes, bytes, bytes]:
        """Packed pre-offset payload, item and post-offset payload of entry"""
        slot = unloaded_slot(child)
        if slot is not None:
            raw = slot.raw()
            item_length = min(slot.item_length, slot.length)
            return dict.__getitem__(child, 'pre_offset_payload'), raw[:item_length], raw[item_length:]
        return (
            child['pre_offset_payload'],
            self.item_block.pack(data=child['item'], ctx=ctx, name=name),
            child['post_offset_payload'],
        )


def slot_lengths(offsets: List[int], region_end: int) -> List[int]:
    """Slot length of each item by absolute item offsets: up to the next bigger offset, or up to the region end"""
    ordered = sorted(set(offsets))
    next_offset = {x: ordered[i + 1] if i + 1 < len(ordered) else region_end for i, x in enumerate(ordered)}
    return [next_offset[x] - x for x in offsets]


def _parse_entry(ctx: ReadContext, slot: Slot) -> dict:
    archive, name = slot.args
    try:
        item = archive.item_block.unpack(ctx=ctx, name=name, read_bytes_amount=slot.item_length)
    except Exception:
        traceback.print_exc()
        ctx.buffer.seek(slot.offset)
        item = {'choice_index': archive.bytes_choice, 'data': ctx.buffer.read(slot.item_length)}
    slot_end = slot.offset + slot.length
    tail = slot_end - ctx.buffer.tell()
    res = {'item': item}
    if archive.has_alias:
        res['alias'] = slot.seed['alias']
    res['pre_offset_payload'] = slot.seed['pre_offset_payload']
    res['post_offset_payload'] = ctx.buffer.read(tail) if tail > 0 else b''
    return res


def read_gap(ctx: ReadContext, start: int, end: int) -> bytes:
    """Bytes between absolute offsets (empty if end is not after start). Buffer position is not changed"""
    if end <= start:
        return b''
    pos = ctx.buffer.tell()
    ctx.buffer.seek(start)
    res = ctx.buffer.read(end - start)
    ctx.buffer.seek(pos)
    return res
