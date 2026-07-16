from io import SEEK_CUR

from library.context import ReadContext
from library.read_blocks import (DeclarativeCompoundBlock,
                                 IntegerBlock, BytesBlock, ArrayBlock, DelegateBlock,
                                 )
from library.read_blocks.misc.value_validators import Eq


class ZeroChunk(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = IntegerBlock(length=4, is_signed=False, value_validator=Eq(0))
        chunk_length = IntegerBlock(length=4, is_signed=False, programmatic_value=lambda ctx: len(ctx.data('payload')))
        payload = (BytesBlock(length=lambda ctx: ctx.data('chunk_length')),
                   {'usage': 'io,doc'})


class Chunk80134001(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = IntegerBlock(length=4, is_signed=False, value_validator=Eq(0x80_13_40_01))
        chunk_length = (
            IntegerBlock(length=4, is_signed=False, programmatic_value=lambda ctx: len(ctx.data('payload'))),
            {'usage': 'io,doc'})
        payload = BytesBlock(length=lambda ctx: ctx.data('chunk_length'))


class Chunk80134010(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = IntegerBlock(length=4, is_signed=False, value_validator=Eq(0x80_13_40_10))
        chunk_length = (
            IntegerBlock(length=4, is_signed=False, programmatic_value=lambda ctx: len(ctx.data('payload'))),
            {'usage': 'io,doc'})
        payload = BytesBlock(length=lambda ctx: ctx.data('chunk_length'))


class Chunk80134020(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = IntegerBlock(length=4, is_signed=False, value_validator=Eq(0x80_13_40_20))
        chunk_length = (
            IntegerBlock(length=4, is_signed=False, programmatic_value=lambda ctx: len(ctx.data('payload'))),
            {'usage': 'io,doc'})
        payload = BytesBlock(length=lambda ctx: ctx.data('chunk_length'))


class Chunk80034020(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = IntegerBlock(length=4, is_signed=False, value_validator=Eq(0x80_03_40_20))
        chunk_length = (
            IntegerBlock(length=4, is_signed=False, programmatic_value=lambda ctx: len(ctx.data('payload'))),
            {'usage': 'io,doc'})
        payload = BytesBlock(length=lambda ctx: ctx.data('chunk_length'))


# not found any of them yet. Keep for future needs
class UnknownChunk(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = IntegerBlock(length=4, is_signed=False)
        chunk_length = (
            IntegerBlock(length=4, is_signed=False, programmatic_value=lambda ctx: len(ctx.data('payload'))),
            {'usage': 'io,doc'})
        payload = BytesBlock(length=lambda ctx: ctx.data('chunk_length'))


def determine_chunks_amount(ctx: ReadContext):
    # read chunk lengths until the end of available bytes
    buffer_pos = ctx.buffer.tell()
    num_chunks = 0
    while ctx.read_bytes_remaining > 0:
        num_chunks += 1
        ctx.buffer.seek(4, SEEK_CUR)
        length = int.from_bytes(ctx.buffer.read(4), byteorder="little", signed=False)
        ctx.buffer.seek(length, SEEK_CUR)
    # return buffer pointer to the original state
    ctx.buffer.seek(buffer_pos)
    return num_chunks


def determine_chunks_class(ctx: ReadContext):
    id = int.from_bytes(ctx.buffer.read(4), byteorder="little", signed=False)
    ctx.buffer.seek(-4, SEEK_CUR)
    id_hex = hex(id).lstrip('0x').ljust(8, '0')
    if id_hex == '00000000':
        class_name = 'ZeroChunk'
    else:
        class_name = 'Chunk' + id_hex
    try:
        return NfsuBinGeometry.Fields.chunks.child.get_choice_index_by_class_name(class_name)
    except IndexError:
        return NfsuBinGeometry.Fields.chunks.child.get_choice_index_by_class_name('UnknownChunk')


class NfsuBinGeometry(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        header = IntegerBlock(length=4, value_validator=Eq(0x80134000))
        data_length = IntegerBlock(length=4)
        chunks = ArrayBlock(length=lambda ctx: determine_chunks_amount(ctx),
                            child=DelegateBlock(possible_blocks=[ZeroChunk(),
                                                                 Chunk80134001(),
                                                                 Chunk80134010(),
                                                                 Chunk80134020(),
                                                                 Chunk80034020(),
                                                                 # UnknownChunk(),
                                                                 ],
                                                choice_index=lambda ctx, **_: determine_chunks_class(ctx)))

    def read(self, ctx: ReadContext, name: str = '', read_bytes_amount=None):
        data = super().read(ctx, name, read_bytes_amount)
        return data
