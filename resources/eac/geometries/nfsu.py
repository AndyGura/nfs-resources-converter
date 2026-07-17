from io import SEEK_CUR

from library.context import ReadContext
from library.read_blocks import (DeclarativeCompoundBlock,
                                 IntegerBlock, BytesBlock, ArrayBlock, DelegateBlock, DecimalBlock,
                                 )
from library.read_blocks.misc.value_validators import Eq, Or
from library.read_blocks.strings import NullTerminatedUTF8Block


class ZeroChunk(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = IntegerBlock(length=4, is_signed=False, value_validator=Eq(0))
        chunk_length = IntegerBlock(length=4, is_signed=False, programmatic_value=lambda ctx: len(ctx.data('payload')))
        payload = (BytesBlock(length=lambda ctx: ctx.data('chunk_length')),
                   {'usage': 'io,doc'})


class NfsuMeshDescriptorChunk(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = IntegerBlock(length=4, is_signed=False, value_validator=Eq(0x80_13_40_10))
        chunk_length = (
            IntegerBlock(length=4, is_signed=False,
                         programmatic_value=lambda ctx: len(ctx.data('payload')) + 157 + len(ctx.data('mesh_name'))),
            {'usage': 'io,doc'})
        # https://chatgpt.com/c/6a5978d6-0080-83eb-9d5c-15cd2885612a
        unk0 = IntegerBlock(length=4, value_validator=Eq(0x00_13_40_11))
        unk1 = IntegerBlock(length=4, value_validator=Eq(0x00_00_00_B0))
        unk2 = IntegerBlock(length=4, value_validator=Eq(0x00_00_00_00))
        unk3 = IntegerBlock(length=4, value_validator=Eq(0x00_00_00_00))
        unk4 = IntegerBlock(length=4, value_validator=Eq(0x00_00_00_00))
        unk5 = IntegerBlock(length=2, value_validator=Eq(0x00_13))
        unk6 = IntegerBlock(length=2, value_validator=Or([0x00_40, 0x00_00]))
        descriptor_metadata = BytesBlock(length=108)
        unk_U = DecimalBlock(length=4, value_validator=Eq(1.0))
        unk_V = DecimalBlock(length=4, value_validator=Eq(0.0))
        unk_W = DecimalBlock(length=4, value_validator=Eq(0.0))
        unk_X = IntegerBlock(length=4, value_validator=Eq(0x00_12_F8_00))
        unk_Y = IntegerBlock(length=4, value_validator=Eq(0x00_12_F8_00))
        unk_Z = IntegerBlock(length=4, value_validator=Eq(0x00_00_00_00))
        mesh_name = NullTerminatedUTF8Block(length=None)
        payload = BytesBlock(length=lambda ctx: ctx.data('chunk_length') - 157 - len(ctx.data('mesh_name')))


class Chunk80134001(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = IntegerBlock(length=4, is_signed=False, value_validator=Eq(0x80_13_40_01))
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
    elif id_hex == '80134010':
        class_name = 'NfsuMeshDescriptorChunk'
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
                                                                 NfsuMeshDescriptorChunk(),
                                                                 Chunk80134001(),
                                                                 Chunk80134020(),
                                                                 Chunk80034020(),
                                                                 # UnknownChunk(),
                                                                 ],
                                                choice_index=lambda ctx, **_: determine_chunks_class(ctx)))
