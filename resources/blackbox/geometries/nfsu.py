from io import SEEK_CUR

from library.context import ReadContext
from library.exceptions import BlockDefinitionException
from library.read_blocks import (DeclarativeCompoundBlock,
                                 IntegerBlock, BytesBlock, ArrayBlock, DelegateBlock, DecimalBlock, CompoundBlock,
                                 )
from library.read_blocks.misc.value_validators import Eq, Or
from library.read_blocks.strings import UTF8Block
from resources.eac.fields.misc import Point3D


class NfsuVec3(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        vector = Point3D(child=DecimalBlock(length=4))
        pad = DecimalBlock(length=4, value_validator=Eq(0.0))


class ZeroChunk(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = IntegerBlock(length=4, is_signed=False, value_validator=Eq(0))
        chunk_length = IntegerBlock(length=4, is_signed=False, programmatic_value=lambda ctx: len(ctx.data('payload')))
        payload = (BytesBlock(length=lambda ctx: ctx.data('chunk_length')),
                   {'usage': 'io,doc'})


# not found any of them yet. Keep for future needs
class UnknownChunk(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = IntegerBlock(length=4, is_signed=False)
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


class NfsuMeshChunk(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = IntegerBlock(length=4, is_signed=False, value_validator=Eq(0x00_13_49_00))
        chunk_length = (
            IntegerBlock(length=4, is_signed=False, programmatic_value=lambda ctx: len(ctx.data('payload')) + 28),
            {'usage': 'io,doc'})
        payload = BytesBlock(length=lambda ctx: ctx.data('chunk_length') - 28)
        faces_amount = IntegerBlock(length=4)
        unk_v = IntegerBlock(length=4, value_validator=Eq(0))
        unk_w = IntegerBlock(length=4, value_validator=Eq(0))
        unk_x = IntegerBlock(length=4, value_validator=Eq(0))
        vertex_amount = IntegerBlock(length=4)
        unk_y = IntegerBlock(length=4, value_validator=Eq(0))
        unk_z = IntegerBlock(length=4, value_validator=Eq(0))


def peek_elevens_length(ctx):
    i = 0
    while ctx.buffer.read(1) == b'\x11':
        i += 1
    ctx.buffer.seek(-i - 1, SEEK_CUR)
    return i


class NfsuMeshFacesChunk(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = IntegerBlock(length=4, value_validator=Eq(0x00_13_4B_03))
        chunk_length = (
            IntegerBlock(length=4, is_signed=False, programmatic_value=lambda ctx: len(ctx.data('faces')) * 6 + len(ctx.data('elevens')) + len(ctx.data('padding'))),
            {'usage': 'io,doc'})
        # some 0x11 values, unknown reason for adding them
        elevens = BytesBlock(length=lambda ctx: peek_elevens_length(ctx))
        faces = ArrayBlock(child=ArrayBlock(child=IntegerBlock(length=2), length=3),
                           length=lambda ctx: ctx.data('../0/data/faces_amount'))
        padding = BytesBlock(length=lambda ctx: ctx.data('chunk_length') - ctx.data('../0/data/faces_amount') * 6 - len(ctx.data('elevens')))

    def read(self, ctx: ReadContext, name: str = '', read_bytes_amount=None):
        data = super().read(ctx, name, read_bytes_amount)
        if data['elevens'] != b'\x11' * len(data['elevens']):
            raise ValueError(f'Invalid elevens data in chunk NfsuMeshFacesChunk: {data["elevens"]}')
        return data


class NfsuVertex(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        position = Point3D(child=DecimalBlock(length=4))
        unk0 = IntegerBlock(length=4)
        unk1 = IntegerBlock(length=4)
        unk2 = IntegerBlock(length=4)
        unk3 = IntegerBlock(length=4)
        u = DecimalBlock(length=4)
        v = DecimalBlock(length=4) # hmm, Bin2Ase renders different values, though x,y,z,u are identical


class MeshVerticesChunk(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = IntegerBlock(length=4, is_signed=False, value_validator=Eq(0x00_13_4B_01))
        chunk_length = (
            IntegerBlock(length=4, is_signed=False, programmatic_value=lambda ctx: len(ctx.data('vertices')) * 36 + len(ctx.data('elevens'))),
            {'usage': 'io,doc'})
        # some 0x11 values, unknown reason for adding them
        elevens = BytesBlock(length=lambda ctx: ctx.data('chunk_length') - ctx.data('../0/data/vertex_amount') * 36, allow_negative_length=True)
        vertices = ArrayBlock(child=NfsuVertex(), length=lambda ctx: ctx.data('../0/data/vertex_amount'))

    # FIXME SUPRA SUPRA_STYLE02_HEADLIGHT_C fails! Reports 114 vertices, but there is not enough data. Although bin2ase returns 114 vertices correctly, with different values
    # Apparently this particular mesh has 24 bytes per vertex, not 36. What is missing?
    def read(self, ctx: ReadContext, name: str = '', read_bytes_amount=None):
        pos_backup = ctx.buffer.tell()
        data = super().read(ctx, name, read_bytes_amount)
        if data['elevens'] != b'\x11' * len(data['elevens']):
            raise ValueError(f'Invalid elevens data in chunk MeshVerticesChunk: {data["elevens"]}')
        if len(data['vertices']) * 36 > data['chunk_length']:
            ctx.buffer.seek(pos_backup + 8)
            raw_payload = ctx.buffer.read(data['chunk_length'])
            print('####')
        return data


class Chunk00134BXX(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        index = IntegerBlock(length=1, value_validator=Or([2, 3]))
        chunk_id = IntegerBlock(length=3, is_signed=False, value_validator=Eq(0x00_13_4B))
        chunk_length = (
            IntegerBlock(length=4, is_signed=False, programmatic_value=lambda ctx: len(ctx.data('payload'))),
            {'usage': 'io,doc'})
        payload = BytesBlock(length=lambda ctx: ctx.data('chunk_length'))


class Chunk80134100(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = IntegerBlock(length=4, is_signed=False, value_validator=Eq(0x80_13_41_00))
        chunk_length = (
            IntegerBlock(length=4, is_signed=False,
                         programmatic_value=lambda ctx: ctx.block.Fields.sub_chunks.estimate_packed_size(ctx.data('sub_chunks'))),
            {'usage': 'io,doc'})
        sub_chunks = ArrayBlock(length=lambda ctx: determine_chunks_amount(ctx,
                                                                           read_bytes_remaining_func=lambda
                                                                               ctx: ctx.data('chunk_length')),
                                child=DelegateBlock(possible_blocks=[
                                    NfsuMeshChunk(),
                                    NfsuMeshFacesChunk(),
                                    MeshVerticesChunk(),
                                    Chunk00134BXX(),
                                    # UnknownChunk(),
                                ],
                                    choice_index=lambda ctx, **_: determine_chunks_class(ctx)))


class Chunk00134002(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = IntegerBlock(length=4, is_signed=False, value_validator=Eq(0x00_13_40_02))
        chunk_length = (
            IntegerBlock(length=4, value_validator=Eq(128)),
            {'usage': 'io,doc'})
        unk_0 = IntegerBlock(length=4)
        unk_1 = IntegerBlock(length=4)
        unk_2 = IntegerBlock(length=4)
        unk_3 = IntegerBlock(length=4)
        file_path = UTF8Block(length=56)
        unk = UTF8Block(length=32)
        unk_4 = IntegerBlock(length=4)
        unk_5 = IntegerBlock(length=4)
        unk_6 = IntegerBlock(length=4)
        unk_7 = IntegerBlock(length=4)
        unk_8 = IntegerBlock(length=4)
        unk_9 = IntegerBlock(length=4)


class Chunk00134003(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = IntegerBlock(length=4, is_signed=False, value_validator=Eq(0x00_13_40_03))
        chunk_length = (
            IntegerBlock(length=4, is_signed=False,
                         programmatic_value=lambda ctx: len(ctx.data('items')) * 8),
            {'usage': 'io,doc'})
        items = ArrayBlock(child=CompoundBlock(fields=[
            ('value', IntegerBlock(length=4), {}),
            ('unk', IntegerBlock(length=4, value_validator=Eq(0)), {})
        ]), length=lambda ctx: int(ctx.data('chunk_length') / 8))


class Chunk00134011(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = IntegerBlock(length=4,  value_validator=Eq(0x00_13_40_11))
        chunk_length = (IntegerBlock(length=4, value_validator=Eq(176)),
                        {'usage': 'io,doc'})
        unk2 = IntegerBlock(length=4, value_validator=Eq(0x00_00_00_00))
        unk3 = IntegerBlock(length=4, value_validator=Eq(0x00_00_00_00))
        unk4 = IntegerBlock(length=4, value_validator=Eq(0x00_00_00_00))
        unk5 = IntegerBlock(length=2, value_validator=Eq(0x00_13))
        unk6 = IntegerBlock(length=2, value_validator=Or([0x00_40, 0x00_00]))
        mesh_id = IntegerBlock(length=4)
        unk7 = IntegerBlock(length=4)
        mesh_flags = IntegerBlock(length=4)  # maybe contains stream count / LOD / material count
        unk10 = IntegerBlock(length=4, value_validator=Eq(0))
        bounding_box_min = NfsuVec3()
        bounding_box_max = NfsuVec3()
        obb_axis0 = NfsuVec3()
        obb_axis1 = NfsuVec3()
        obb_axis2 = NfsuVec3()

        # is it a quaternion?
        unk_float0 = DecimalBlock(length=4)
        unk_float1 = DecimalBlock(length=4)
        unk_float2 = DecimalBlock(length=4)
        unk_U = DecimalBlock(length=4, value_validator=Eq(1.0))

        unk_V = DecimalBlock(length=4, value_validator=Eq(0.0))
        unk_W = DecimalBlock(length=4, value_validator=Eq(0.0))
        unk_X = IntegerBlock(length=4, value_validator=Eq(0x00_12_F8_00))
        unk_Y = IntegerBlock(length=4, value_validator=Eq(0x00_12_F8_00))
        unk_Z = IntegerBlock(length=4, value_validator=Eq(0x00_00_00_00))
        mesh_name = UTF8Block(length=28)


class Chunk00134012(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = IntegerBlock(length=4, is_signed=False, value_validator=Eq(0x00_13_40_12))
        chunk_length = (
            IntegerBlock(length=4, is_signed=False,
                         programmatic_value=lambda ctx: len(ctx.data('items')) * 8),
            {'usage': 'io,doc'})
        items = ArrayBlock(child=CompoundBlock(fields=[
            ('value', IntegerBlock(length=4), {}),
            ('unk', IntegerBlock(length=4, value_validator=Eq(0)), {})
        ]), length=lambda ctx: int(ctx.data('chunk_length') / 8))


class Chunk00134013(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = IntegerBlock(length=4, is_signed=False, value_validator=Eq(0x00_13_40_13))
        chunk_length = (
            IntegerBlock(length=4, is_signed=False,
                         programmatic_value=lambda ctx: len(ctx.data('items')) * 8),
            {'usage': 'io,doc'})
        items = ArrayBlock(child=CompoundBlock(fields=[
            ('value', IntegerBlock(length=4), {}),
            ('unk', IntegerBlock(length=4, value_validator=Eq(0)), {})
        ]), length=lambda ctx: int(ctx.data('chunk_length') / 8))



class Chunk001340XX(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        index = IntegerBlock(length=1, value_validator=Or([4, 23, 24, 25, 0x1A]))
        chunk_id = IntegerBlock(length=3, is_signed=False, value_validator=Eq(0x00_13_40))
        chunk_length = (
            IntegerBlock(length=4, is_signed=False,
                         programmatic_value=lambda ctx: len(ctx.data('payload'))),
            {'usage': 'io,doc'})
        payload = BytesBlock(length=lambda ctx: ctx.data('chunk_length'))

    def read(self, ctx: ReadContext, name: str = '', read_bytes_amount=None):
        data = super().read(ctx, name, read_bytes_amount)
        if data['index'] == 23 and len(data['payload']) != 12:
            raise BlockDefinitionException('23 -> 12 error')
        elif data['index'] == 18:
            print()
            print('###', data['index'], len(data['payload']), [hex(x) for x in list(data['payload'][:24])])
            print()
        return data


class Chunk80134008(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = IntegerBlock(length=4, is_signed=False, value_validator=Eq(0x80_13_40_08))
        chunk_length = (
            IntegerBlock(length=4, is_signed=False,
                         programmatic_value=lambda ctx: len(ctx.data('payload'))),
            {'usage': 'io,doc'})
        payload = BytesBlock(length=lambda ctx: ctx.data('chunk_length'))


class NfsuMeshDescriptorChunk(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = IntegerBlock(length=4, is_signed=False, value_validator=Eq(0x80_13_40_10))
        chunk_length = (
            IntegerBlock(length=4, is_signed=False,
                         programmatic_value=lambda ctx: ctx.block.Fields.sub_chunks.estimate_packed_size(
                             ctx.data('sub_chunks'))),
            {'usage': 'io,doc'})
        sub_chunks = ArrayBlock(length=lambda ctx: determine_chunks_amount(ctx,
                                                                           read_bytes_remaining_func=lambda
                                                                               ctx: ctx.data('chunk_length')),
                                child=DelegateBlock(possible_blocks=[Chunk00134011(),
                                                                     Chunk00134012(),
                                                                     Chunk00134013(),
                                                                     Chunk80134100(),
                                                                     Chunk001340XX(),
                                                                     # UnknownChunk(),
                                                                     ],
                                                    choice_index=lambda ctx, **_: determine_chunks_class(ctx)))


class Chunk80134001(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = IntegerBlock(length=4, is_signed=False, value_validator=Eq(0x80_13_40_01))
        chunk_length = (
            IntegerBlock(length=4, is_signed=False,
                         programmatic_value=lambda ctx: ctx.block.Fields.sub_chunks.estimate_packed_size(ctx.data('sub_chunks'))),
            {'usage': 'io,doc'})
        # always 3 or 4 blocks
        sub_chunks = ArrayBlock(length=lambda ctx: determine_chunks_amount(ctx,
                                                                           read_bytes_remaining_func=lambda
                                                                               ctx: ctx.data('chunk_length')),
                                child=DelegateBlock(possible_blocks=[
                                    Chunk00134002(),
                                    Chunk00134003(),
                                    Chunk001340XX(),
                                    Chunk80134008(),
                                    # UnknownChunk(),
                                ],
                                    choice_index=lambda ctx, **_: determine_chunks_class(ctx)))


class Chunk80134020(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = IntegerBlock(length=4, is_signed=False, value_validator=Eq(0x80_13_40_20))
        chunk_length = (
            IntegerBlock(length=4, is_signed=False, programmatic_value=lambda ctx: len(ctx.data('payload'))),
            {'usage': 'io,doc'})
        payload = BytesBlock(length=lambda ctx: ctx.data('chunk_length'))


def determine_chunks_amount(ctx: ReadContext, read_bytes_remaining_func=None):
    if read_bytes_remaining_func is not None:
        read_bytes_remaining = read_bytes_remaining_func(ctx)
    else:
        read_bytes_remaining = ctx.read_bytes_remaining
    # read chunk lengths until the end of available bytes
    buffer_pos = ctx.buffer.tell()
    num_chunks = 0
    while read_bytes_remaining > 0:
        num_chunks += 1
        ctx.buffer.seek(4, SEEK_CUR)
        length = int.from_bytes(ctx.buffer.read(4), byteorder="little", signed=False)
        ctx.buffer.seek(length, SEEK_CUR)
        read_bytes_remaining -= 8 + length
    # return buffer pointer to the original state
    ctx.buffer.seek(buffer_pos)
    return num_chunks


def determine_chunks_class(ctx: ReadContext):
    id = int.from_bytes(ctx.buffer.read(4), byteorder="little", signed=False)
    ctx.buffer.seek(-4, SEEK_CUR)
    id_hex = hex(id).lstrip('0x').rjust(8, '0').upper()
    if id_hex == '00000000':
        class_name = 'ZeroChunk'
    elif id_hex == '80134010':
        class_name = 'NfsuMeshDescriptorChunk'
    elif id_hex == '00134B03':
        class_name = 'NfsuMeshFacesChunk'
    elif id_hex == '00134900':
        class_name = 'NfsuMeshChunk'
    elif id_hex == '00134B01':
        class_name = 'MeshVerticesChunk'
    elif id_hex.startswith('001340') and not id_hex in ['00134002', '00134003', '00134011', '00134012', '00134013']:
        class_name = 'Chunk001340XX'
    elif id_hex.startswith('00134B') and not id_hex in ['00134B01']:
        class_name = 'Chunk00134BXX'
    else:
        class_name = 'Chunk' + id_hex
    try:
        return ctx.block.child.get_choice_index_by_class_name(class_name)
    except ValueError:
        raise Exception('Unknown chunk: ' + class_name)
        # return ctx.block.child.get_choice_index_by_class_name('UnknownChunk')


class NfsuBinGeometry(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        header = IntegerBlock(length=4, value_validator=Eq(0x80134000))
        data_length = IntegerBlock(length=4)
        chunks = ArrayBlock(length=lambda ctx: determine_chunks_amount(ctx),
                            child=DelegateBlock(possible_blocks=[ZeroChunk(),
                                                                 NfsuMeshDescriptorChunk(),
                                                                 Chunk80134001(),
                                                                 Chunk80034020(),
                                                                 # UnknownChunk(),
                                                                 ],
                                                choice_index=lambda ctx, **_: determine_chunks_class(ctx)))

    def serializer_class(self):
        from serializers.geometries import NfsuBinGeometrySerializer
        return NfsuBinGeometrySerializer


