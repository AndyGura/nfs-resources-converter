from io import SEEK_CUR
from typing import Dict, List

from library.read_blocks import ArrayBlock, DataBlock, DelegateBlock, IntegerBlock
from resources.blackbox.geometries.nfsu import _CHUNK_LENGTH_DESCR, UnknownChunk, determine_chunks_amount

# Black Box bundles (NFS Underground *.BUN, *.BIN, uncompressed *.lzc) are trees of chunks: 32-bit chunk id,
# 32-bit payload length, payload. Chunks with the highest bit of id set are containers of other chunks.


def peek_chunk_id(ctx) -> int:
    chunk_id = int.from_bytes(ctx.buffer.read(4), 'little')
    ctx.buffer.seek(-4, SEEK_CUR)
    return chunk_id


def chunk_blocks_by_id(blocks: List[DataBlock]) -> Dict[int, int]:
    """Chunk id -> index of block, from `Eq` validators of `chunk_id` fields"""
    blocks_by_id = {}
    for i, block in enumerate(blocks):
        # NfsuBinGeometry names its chunk id field "header"
        fields = getattr(block, 'field_blocks_map', {})
        chunk_id_block = fields.get('chunk_id') or fields.get('header')
        validator = chunk_id_block.value_validator if chunk_id_block else None
        if validator is not None and hasattr(validator, 'expected_value'):
            blocks_by_id[validator.expected_value] = i
    return blocks_by_id


def chunk_delegate(possible_blocks: List[DataBlock]) -> DelegateBlock:
    """One chunk of any of given kinds, picked by chunk id. Unknown chunks are read as `UnknownChunk`"""
    blocks = list(possible_blocks) + [UnknownChunk()]
    blocks_by_id = chunk_blocks_by_id(blocks[:-1])
    return DelegateBlock(
        possible_blocks=blocks,
        choice_index=(
            lambda ctx, **_: blocks_by_id.get(peek_chunk_id(ctx), len(blocks) - 1),
            'by chunk id, `UnknownChunk` for unknown ids',
        ),
    )


def nfsu_sub_chunks_field(possible_blocks: List[DataBlock], description: str):
    """Field with child chunks of a container chunk, read until its payload is exhausted"""
    return (
        ArrayBlock(
            length=(
                lambda ctx: determine_chunks_amount(
                    ctx, read_bytes_remaining_func=lambda ctx: ctx.data('chunk_length')
                ),
                'until the end of chunk',
            ),
            child=chunk_delegate(possible_blocks),
        ),
        {'description': description},
    )


def container_chunk_length():
    """Field with length of a container chunk, computed from its `sub_chunks` on write"""
    return (
        IntegerBlock(
            length=4,
            programmatic_value=lambda ctx: ctx.block.field_blocks_map['sub_chunks'].estimate_packed_size(
                ctx.data('sub_chunks')
            ),
        ),
        {'usage': 'io,doc', 'description': _CHUNK_LENGTH_DESCR},
    )
