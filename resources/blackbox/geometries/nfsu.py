from io import SEEK_CUR
from typing import Dict

from library.context import ReadContext
from library.exceptions import BlockDefinitionException
from library.read_blocks import (
    DeclarativeCompoundBlock,
    IntegerBlock,
    BytesBlock,
    ArrayBlock,
    DelegateBlock,
    DecimalBlock,
    CompoundBlock,
)
from library.read_blocks.misc.value_validators import Eq, Or
from library.read_blocks.strings import UTF8Block
from resources.eac.fields.misc import Point3D

# All chunks of the file share the same 8-byte header: 32-bit chunk id followed by 32-bit payload length.
# Container chunks (id starting with 0x80) hold a sequence of child chunks as their payload.
_CHUNK_ID_DESCR = 'Chunk ID'
_CHUNK_LENGTH_DESCR = 'Length of the chunk payload in bytes (everything after this field)'
_ELEVENS_DESCR = (
    'Alignment filler: a run of 0x11 bytes before the actual payload, so that the payload starts at an aligned offset'
)


class NfsuVec3(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {**super().schema, 'block_description': 'A 3D vector padded to 16 bytes'}

    class Fields(DeclarativeCompoundBlock.Fields):
        vector = (Point3D(child=DecimalBlock(length=4)), {'description': 'Vector components'})
        pad = (DecimalBlock(length=4, value_validator=Eq(0.0)), {'description': 'Padding, always 0'})


class ZeroChunk(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Padding chunk with id 0: filler between meaningful chunks, used for alignment. '
            'Payload has no meaning',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = (IntegerBlock(length=4, is_signed=False, value_validator=Eq(0)), {'description': _CHUNK_ID_DESCR})
        chunk_length = (
            IntegerBlock(length=4, is_signed=False, programmatic_value=lambda ctx: len(ctx.data('payload'))),
            {'description': _CHUNK_LENGTH_DESCR},
        )
        payload = (
            BytesBlock(length=lambda ctx: ctx.data('chunk_length')),
            {'usage': 'io,doc', 'description': 'Filler bytes'},
        )


class UnknownChunk(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'A chunk not decoded by the parser: header + raw payload',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = (IntegerBlock(length=4, is_signed=False), {'description': _CHUNK_ID_DESCR})
        chunk_length = (
            IntegerBlock(length=4, is_signed=False, programmatic_value=lambda ctx: len(ctx.data('payload'))),
            {'usage': 'io,doc', 'description': _CHUNK_LENGTH_DESCR},
        )
        payload = (BytesBlock(length=lambda ctx: ctx.data('chunk_length')), {'description': 'Raw chunk payload'})


class Chunk80034020(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {**super().schema, 'block_description': 'The last chunk of the file, purpose unknown'}

    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = (
            IntegerBlock(length=4, is_signed=False, value_validator=Eq(0x80_03_40_20)),
            {'description': _CHUNK_ID_DESCR},
        )
        chunk_length = (
            IntegerBlock(length=4, is_signed=False, programmatic_value=lambda ctx: len(ctx.data('payload'))),
            {'usage': 'io,doc', 'description': _CHUNK_LENGTH_DESCR},
        )
        payload = (BytesBlock(length=lambda ctx: ctx.data('chunk_length')), {'is_unknown': True})


class NfsuMeshChunk(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Mesh info chunk: amounts of faces and vertices of the mesh, used to read the '
            'faces and vertices chunks of the same mesh data container',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = (
            IntegerBlock(length=4, is_signed=False, value_validator=Eq(0x00_13_49_00)),
            {'description': _CHUNK_ID_DESCR},
        )
        chunk_length = (
            IntegerBlock(length=4, is_signed=False, programmatic_value=lambda ctx: len(ctx.data('payload')) + 28),
            {'usage': 'io,doc', 'description': _CHUNK_LENGTH_DESCR},
        )
        payload = (
            BytesBlock(length=lambda ctx: ctx.data('chunk_length') - 28),
            {'description': 'Unknown data, starts with 0x11 alignment filler bytes', 'is_unknown': True},
        )
        faces_amount = (IntegerBlock(length=4), {'description': 'Amount of faces (triangles) of the mesh'})
        unk_v = (IntegerBlock(length=4, value_validator=Eq(0)), {'is_unknown': True})
        unk_w = (IntegerBlock(length=4, value_validator=Eq(0)), {'is_unknown': True})
        unk_x = (IntegerBlock(length=4, value_validator=Eq(0)), {'is_unknown': True})
        vertex_amount = (IntegerBlock(length=4), {'description': 'Amount of vertices of the mesh'})
        unk_y = (IntegerBlock(length=4, value_validator=Eq(0)), {'is_unknown': True})
        unk_z = (IntegerBlock(length=4, value_validator=Eq(0)), {'is_unknown': True})


def elevens_length(ctx, alignment: int = 0x10):
    """Length of 0x11 alignment filler: chunk payloads start at an offset aligned to 16 (vertices: 128) bytes from
    the beginning of the file"""
    return -ctx.buffer.tell() % alignment


class NfsuMeshFacesChunk(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Mesh faces: a triangle list. Amount of faces is defined by the mesh info chunk '
            '(the first chunk of the same mesh data container)',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = (IntegerBlock(length=4, value_validator=Eq(0x00_13_4B_03)), {'description': _CHUNK_ID_DESCR})
        chunk_length = (
            IntegerBlock(
                length=4,
                is_signed=False,
                programmatic_value=lambda ctx: (
                    len(ctx.data('faces')) * 6 + len(ctx.data('elevens')) + len(ctx.data('padding'))
                ),
            ),
            {'usage': 'io,doc', 'description': _CHUNK_LENGTH_DESCR},
        )
        # some 0x11 values, unknown reason for adding them
        elevens = (
            BytesBlock(length=(lambda ctx: elevens_length(ctx), 'up to 16-bytes alignment')),
            {'description': _ELEVENS_DESCR},
        )
        faces = (
            ArrayBlock(
                child=ArrayBlock(child=IntegerBlock(length=2), length=3),
                length=lambda ctx: ctx.data('../0/data/faces_amount'),
            ),
            {'description': 'Triangles: 3 vertex indexes each, pointing to the vertices chunk of the same mesh'},
        )
        padding = (
            BytesBlock(
                length=lambda ctx: (
                    ctx.data('chunk_length') - ctx.data('../0/data/faces_amount') * 6 - len(ctx.data('elevens'))
                )
            ),
            {'description': 'Padding to the end of the chunk'},
        )

    def read(self, ctx: ReadContext, name: str = '', read_bytes_amount=None):
        data = super().read(ctx, name, read_bytes_amount)
        if data['elevens'] != b'\x11' * len(data['elevens']):
            raise ValueError(f'Invalid elevens data in chunk NfsuMeshFacesChunk: {data["elevens"]}')
        return data


class NfsuVertex(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'A single mesh vertex with normal (36 bytes). The most common vertex layout',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        position = (Point3D(child=DecimalBlock(length=4)), {'description': 'Vertex position'})
        unk0 = (
            IntegerBlock(length=4),
            {'description': 'Presumably X component of the vertex normal, stored as 32-bit float', 'is_unknown': True},
        )
        unk1 = (
            IntegerBlock(length=4),
            {'description': 'Presumably Y component of the vertex normal, stored as 32-bit float', 'is_unknown': True},
        )
        unk2 = (
            IntegerBlock(length=4),
            {'description': 'Presumably Z component of the vertex normal, stored as 32-bit float', 'is_unknown': True},
        )
        unk3 = (IntegerBlock(length=4), {'description': 'Presumably vertex color, 32-bit ARGB', 'is_unknown': True})
        u = (DecimalBlock(length=4), {'description': 'U texture coordinate'})
        v = (
            DecimalBlock(length=4),  # hmm, Bin2Ase renders different values, though x,y,z,u are identical
            {'description': 'V texture coordinate'},
        )


class NfsuVertexNoNormal(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'A single mesh vertex without normal (24 bytes). Used by a few meshes, e.g. '
            'SUPRA_STYLE02_HEADLIGHT_C. Same layout as the 36-byte vertex with the normal '
            'omitted (Direct3D FVF order: position, diffuse color, texture coordinates)',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        position = (Point3D(child=DecimalBlock(length=4)), {'description': 'Vertex position'})
        unk3 = (IntegerBlock(length=4), {'description': 'Presumably vertex color, 32-bit ARGB', 'is_unknown': True})
        u = (DecimalBlock(length=4), {'description': 'U texture coordinate'})
        v = (DecimalBlock(length=4), {'description': 'V texture coordinate'})


class NfsuVertexSkinned(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'A single mesh vertex with normal and skinning data (60 bytes). Used by a few '
            'world meshes (flags 0x4081 in the mesh info chunk)',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        position = (Point3D(child=DecimalBlock(length=4)), {'description': 'Vertex position'})
        normal = (Point3D(child=DecimalBlock(length=4)), {'description': 'Vertex normal'})
        unk3 = (IntegerBlock(length=4), {'description': 'Presumably vertex color, 32-bit ARGB', 'is_unknown': True})
        u = (DecimalBlock(length=4), {'description': 'U texture coordinate'})
        v = (DecimalBlock(length=4), {'description': 'V texture coordinate'})
        blend_weights = (Point3D(child=DecimalBlock(length=4)), {'description': 'Blend weights', 'is_unknown': True})
        blend_indices = (Point3D(child=DecimalBlock(length=4)), {'description': 'Blend indices', 'is_unknown': True})


# Size in bytes of each vertex layout, in the order of MeshVerticesChunk.Fields.vertices possible blocks
_NFSU_VERTEX_SIZES = [36, 24, 60]


def _vertex_layout_index(ctx):
    # The vertex layout is not stored explicitly (or not found yet): it is the vertex size that fills the payload
    # after the alignment filler. Raw bytes (the last choice) if there are no vertices, or the size is not known
    vertex_amount = ctx.data('../0/data/vertex_amount')
    payload_length = ctx.data('chunk_length') - len(ctx.data('elevens'))
    for i, size in enumerate(_NFSU_VERTEX_SIZES):
        if vertex_amount and payload_length == vertex_amount * size:
            return i
    return len(_NFSU_VERTEX_SIZES)


class MeshVerticesChunk(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Mesh vertices. Amount of vertices is defined by the mesh info chunk (the first '
            'chunk of the same mesh data container). Vertex size (36, 24 or 60 bytes) is '
            'determined by the chunk length',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = (
            IntegerBlock(length=4, is_signed=False, value_validator=Eq(0x00_13_4B_01)),
            {'description': _CHUNK_ID_DESCR},
        )
        chunk_length = (
            IntegerBlock(
                length=4,
                is_signed=False,
                programmatic_value=lambda ctx: (
                    len(ctx.data('elevens'))
                    + (
                        len(ctx.data('vertices')['data'])
                        if ctx.data('vertices')['choice_index'] == len(_NFSU_VERTEX_SIZES)
                        else len(ctx.data('vertices')['data'])
                        * _NFSU_VERTEX_SIZES[ctx.data('vertices')['choice_index']]
                    )
                ),
            ),
            {'usage': 'io,doc', 'description': _CHUNK_LENGTH_DESCR},
        )
        elevens = (
            BytesBlock(length=(lambda ctx: elevens_length(ctx, 0x80), 'up to 128-bytes alignment')),
            {'description': _ELEVENS_DESCR},
        )
        vertices = (
            DelegateBlock(
                possible_blocks=[
                    ArrayBlock(child=NfsuVertex(), length=lambda ctx: ctx.data('../0/data/vertex_amount')),
                    ArrayBlock(child=NfsuVertexNoNormal(), length=lambda ctx: ctx.data('../0/data/vertex_amount')),
                    ArrayBlock(child=NfsuVertexSkinned(), length=lambda ctx: ctx.data('../0/data/vertex_amount')),
                    BytesBlock(length=lambda ctx: ctx.data('chunk_length') - len(ctx.data('elevens'))),
                ],
                choice_index=(lambda ctx, **_: _vertex_layout_index(ctx), 'depends on chunk_length'),
            ),
            {
                'description': 'Vertices: 36-byte vertices with normal, 24-byte vertices without normal or 60-byte '
                'vertices with normal and skinning data, whichever fills the chunk. Raw bytes if the mesh '
                'has no vertices'
            },
        )

    def read(self, ctx: ReadContext, name: str = '', read_bytes_amount=None):
        data = super().read(ctx, name, read_bytes_amount)
        if data['elevens'] != b'\x11' * len(data['elevens']):
            raise ValueError(f'Invalid elevens data in chunk MeshVerticesChunk: {data["elevens"]}')
        return data


class NfsuMeshMaterial(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'A part of the mesh drawn with one texture: a range of the triangle list',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        bounding_box_min = (Point3D(child=DecimalBlock(length=4)), {'description': 'Bounding box minimum corner'})
        indices_amount = (IntegerBlock(length=4), {'description': 'Amount of vertex indexes (3 per triangle)'})
        bounding_box_max = (Point3D(child=DecimalBlock(length=4)), {'description': 'Bounding box maximum corner'})
        texture_index = (
            IntegerBlock(length=4),
            {'description': 'Index of texture id in the texture ids chunk (0x00134012) of the mesh'},
        )
        light_material_index = (IntegerBlock(length=4, is_signed=True), {'is_unknown': True})
        unk = (ArrayBlock(child=IntegerBlock(length=4), length=4), {'is_unknown': True})
        indices_offset = (
            IntegerBlock(length=4),
            {'description': 'Index of the first vertex index in the faces chunk: sum of previous `indices_amount`'},
        )
        flags = (IntegerBlock(length=4), {'is_unknown': True})


class NfsuMeshMaterialsChunk(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Mesh materials: the triangle list of the mesh split into ranges with their own '
            'texture',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = (
            IntegerBlock(length=4, is_signed=False, value_validator=Eq(0x00_13_4B_02)),
            {'description': _CHUNK_ID_DESCR},
        )
        chunk_length = (
            IntegerBlock(
                length=4,
                is_signed=False,
                programmatic_value=lambda ctx: len(ctx.data('materials')) * 60 + len(ctx.data('elevens')),
            ),
            {'usage': 'io,doc', 'description': _CHUNK_LENGTH_DESCR},
        )
        elevens = (
            BytesBlock(length=(lambda ctx: elevens_length(ctx), 'up to 16-bytes alignment')),
            {'description': _ELEVENS_DESCR},
        )
        materials = (
            ArrayBlock(
                child=NfsuMeshMaterial(), length=lambda ctx: (ctx.data('chunk_length') - len(ctx.data('elevens'))) // 60
            ),
            {'description': 'Materials, in the order of their ranges in the faces chunk'},
        )


class Chunk80134100(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Mesh data container: holds the mesh info chunk (always first), vertices chunk '
            'and faces chunk of a single mesh',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = (
            IntegerBlock(length=4, is_signed=False, value_validator=Eq(0x80_13_41_00)),
            {'description': _CHUNK_ID_DESCR},
        )
        chunk_length = (
            IntegerBlock(
                length=4,
                is_signed=False,
                programmatic_value=lambda ctx: ctx.block.field_blocks_map['sub_chunks'].estimate_packed_size(
                    ctx.data('sub_chunks')
                ),
            ),
            {'usage': 'io,doc', 'description': _CHUNK_LENGTH_DESCR},
        )
        sub_chunks = (
            ArrayBlock(
                length=lambda ctx: determine_chunks_amount(
                    ctx, read_bytes_remaining_func=lambda ctx: ctx.data('chunk_length')
                ),
                child=DelegateBlock(
                    possible_blocks=[
                        NfsuMeshChunk(),
                        NfsuMeshFacesChunk(),
                        MeshVerticesChunk(),
                        NfsuMeshMaterialsChunk(),
                        # UnknownChunk(),
                    ],
                    choice_index=lambda ctx, **_: determine_chunks_class(ctx),
                ),
            ),
            {
                'description': 'Child chunks, read until the payload is exhausted. Block class picked '
                'according to the chunk id'
            },
        )


class Chunk00134002(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {**super().schema, 'block_description': 'File info: original path of the file and unknown values'}

    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = (
            IntegerBlock(length=4, is_signed=False, value_validator=Eq(0x00_13_40_02)),
            {'description': _CHUNK_ID_DESCR},
        )
        chunk_length = (
            IntegerBlock(length=4, value_validator=Eq(128)),
            {'usage': 'io,doc', 'description': _CHUNK_LENGTH_DESCR},
        )
        unk_0 = (IntegerBlock(length=4), {'is_unknown': True})
        unk_1 = (IntegerBlock(length=4), {'is_unknown': True})
        unk_2 = (IntegerBlock(length=4), {'is_unknown': True})
        unk_3 = (
            IntegerBlock(length=4),
            {
                'description': 'Amount of meshes in the file? Equals to the amount of items in the mesh ids chunk',
                'is_unknown': True,
            },
        )
        file_path = (
            UTF8Block(length=56),
            {
                'description': 'Path of this file in the original development environment, e.g. '
                '"..\\PC\\CD\\CARS\\S2000\\GEOMETRY.BIN"'
            },
        )
        unk = (UTF8Block(length=32), {'description': 'Some name, e.g. "DEFAULT"', 'is_unknown': True})
        unk_4 = (IntegerBlock(length=4), {'is_unknown': True})
        unk_5 = (IntegerBlock(length=4), {'is_unknown': True})
        unk_6 = (IntegerBlock(length=4), {'is_unknown': True})
        unk_7 = (IntegerBlock(length=4), {'is_unknown': True})
        unk_8 = (IntegerBlock(length=4), {'is_unknown': True})
        unk_9 = (IntegerBlock(length=4), {'is_unknown': True})


class Chunk00134003(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'List of mesh ids contained in the file, one item per mesh descriptor chunk',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = (
            IntegerBlock(length=4, is_signed=False, value_validator=Eq(0x00_13_40_03)),
            {'description': _CHUNK_ID_DESCR},
        )
        chunk_length = (
            IntegerBlock(length=4, is_signed=False, programmatic_value=lambda ctx: len(ctx.data('items')) * 8),
            {'usage': 'io,doc', 'description': _CHUNK_LENGTH_DESCR},
        )
        items = (
            ArrayBlock(
                child=CompoundBlock(
                    fields=[
                        ('value', IntegerBlock(length=4), {}),
                        ('unk', IntegerBlock(length=4, value_validator=Eq(0)), {}),
                    ],
                    inline_description='Two 32-bit unsigned integers (little-endian): value, then unk (always 0)',
                ),
                length=lambda ctx: int(ctx.data('chunk_length') / 8),
            ),
            {'description': 'Mesh ids: `value` equals to `mesh_id` of the corresponding mesh header chunk'},
        )


class Chunk00134011(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Mesh header: id, name, bounding volume and flags of a single mesh',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = (IntegerBlock(length=4, value_validator=Eq(0x00_13_40_11)), {'description': _CHUNK_ID_DESCR})
        chunk_length = (
            IntegerBlock(length=4, programmatic_value=lambda ctx: 176 + len(ctx.data('elevens'))),
            {'usage': 'io,doc', 'description': _CHUNK_LENGTH_DESCR + ': 176 + length of alignment filler'},
        )
        elevens = (
            BytesBlock(length=(lambda ctx: elevens_length(ctx), 'up to 16-bytes alignment')),
            {'usage': 'io,doc', 'description': _ELEVENS_DESCR},
        )
        unk2 = (IntegerBlock(length=4, value_validator=Eq(0x00_00_00_00)), {'is_unknown': True})
        unk3 = (IntegerBlock(length=4, value_validator=Eq(0x00_00_00_00)), {'is_unknown': True})
        unk4 = (IntegerBlock(length=4, value_validator=Eq(0x00_00_00_00)), {'is_unknown': True})
        unk5 = (IntegerBlock(length=2, value_validator=Eq(0x00_13)), {'is_unknown': True})
        unk6 = (IntegerBlock(length=2, value_validator=Or([0x00_40, 0x00_00])), {'is_unknown': True})
        mesh_id = (IntegerBlock(length=4), {'description': 'Mesh id (hash), listed in the mesh ids chunk of the file'})
        unk7 = (
            IntegerBlock(length=4),
            {'description': 'Amount of faces? Equals to `faces_amount` of the mesh info chunk', 'is_unknown': True},
        )
        mesh_flags = (
            IntegerBlock(length=4),  # maybe contains stream count / LOD / material count
            {'description': 'Mesh flags. Maybe contains stream count / LOD / material count', 'is_unknown': True},
        )
        unk10 = (IntegerBlock(length=4, value_validator=Eq(0)), {'is_unknown': True})
        bounding_box_min = (NfsuVec3(), {'description': 'Minimum corner of the axis-aligned bounding box of the mesh'})
        bounding_box_max = (NfsuVec3(), {'description': 'Maximum corner of the axis-aligned bounding box of the mesh'})
        obb_axis0 = (NfsuVec3(), {'description': 'First axis of the oriented bounding box'})
        obb_axis1 = (NfsuVec3(), {'description': 'Second axis of the oriented bounding box'})
        obb_axis2 = (NfsuVec3(), {'description': 'Third axis of the oriented bounding box'})

        # is it a quaternion?
        unk_float0 = (
            DecimalBlock(length=4),
            {'description': 'Is it a quaternion (with the next 3 floats)?', 'is_unknown': True},
        )
        unk_float1 = (DecimalBlock(length=4), {'is_unknown': True})
        unk_float2 = (DecimalBlock(length=4), {'is_unknown': True})
        unk_U = (DecimalBlock(length=4, value_validator=Eq(1.0)), {'is_unknown': True})

        unk_V = (DecimalBlock(length=4, value_validator=Eq(0.0)), {'is_unknown': True})
        unk_W = (DecimalBlock(length=4, value_validator=Eq(0.0)), {'is_unknown': True})
        unk_X = (IntegerBlock(length=4, value_validator=Eq(0x00_12_F8_00)), {'is_unknown': True})
        unk_Y = (IntegerBlock(length=4, value_validator=Eq(0x00_12_F8_00)), {'is_unknown': True})
        unk_Z = (IntegerBlock(length=4, value_validator=Eq(0x00_00_00_00)), {'is_unknown': True})
        mesh_name = (
            UTF8Block(length=28),
            {'description': 'Mesh name, e.g. "S2000_KIT08_FRONT_BUMPER_A". Used as the name of exported mesh'},
        )


class Chunk00134012(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'A list of 32-bit values (hashes) of the mesh, presumably texture ids',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = (
            IntegerBlock(length=4, is_signed=False, value_validator=Eq(0x00_13_40_12)),
            {'description': _CHUNK_ID_DESCR},
        )
        chunk_length = (
            IntegerBlock(length=4, is_signed=False, programmatic_value=lambda ctx: len(ctx.data('items')) * 8),
            {'usage': 'io,doc', 'description': _CHUNK_LENGTH_DESCR},
        )
        items = (
            ArrayBlock(
                child=CompoundBlock(
                    fields=[
                        ('value', IntegerBlock(length=4), {}),
                        ('unk', IntegerBlock(length=4, value_validator=Eq(0)), {}),
                    ],
                    inline_description='Two 32-bit unsigned integers (little-endian): value, then unk (always 0)',
                ),
                length=lambda ctx: int(ctx.data('chunk_length') / 8),
            ),
            {'description': 'Items', 'is_unknown': True},
        )


class Chunk00134013(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'A list of 32-bit values (hashes) of the mesh, presumably shader/material ids',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = (
            IntegerBlock(length=4, is_signed=False, value_validator=Eq(0x00_13_40_13)),
            {'description': _CHUNK_ID_DESCR},
        )
        chunk_length = (
            IntegerBlock(length=4, is_signed=False, programmatic_value=lambda ctx: len(ctx.data('items')) * 8),
            {'usage': 'io,doc', 'description': _CHUNK_LENGTH_DESCR},
        )
        items = (
            ArrayBlock(
                child=CompoundBlock(
                    fields=[
                        ('value', IntegerBlock(length=4), {}),
                        ('unk', IntegerBlock(length=4, value_validator=Eq(0)), {}),
                    ],
                    inline_description='Two 32-bit unsigned integers (little-endian): value, then unk (always 0)',
                ),
                length=lambda ctx: int(ctx.data('chunk_length') / 8),
            ),
            {'description': 'Items', 'is_unknown': True},
        )


class Chunk001340XX(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Unknown chunk with id 0x001340XX, kept as raw bytes. Known ids: 0x00134004 in '
            'the file info container (20-byte records per mesh, starting with mesh id); '
            '0x00134017, 0x00134018, 0x00134019, 0x0013401A in mesh descriptors',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        index = (
            IntegerBlock(length=1, value_validator=Or([4, 23, 24, 25, 0x1A])),
            {'description': 'Lowest byte of the chunk id'},
        )
        chunk_id = (
            IntegerBlock(length=3, is_signed=False, value_validator=Eq(0x00_13_40)),
            {'description': 'Upper 3 bytes of the chunk id'},
        )
        chunk_length = (
            IntegerBlock(length=4, is_signed=False, programmatic_value=lambda ctx: len(ctx.data('payload'))),
            {'usage': 'io,doc', 'description': _CHUNK_LENGTH_DESCR},
        )
        payload = (BytesBlock(length=lambda ctx: ctx.data('chunk_length')), {'is_unknown': True})

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
    @property
    def schema(self) -> Dict:
        return {**super().schema, 'block_description': 'Unknown chunk of the file info container, usually empty'}

    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = (
            IntegerBlock(length=4, is_signed=False, value_validator=Eq(0x80_13_40_08)),
            {'description': _CHUNK_ID_DESCR},
        )
        chunk_length = (
            IntegerBlock(length=4, is_signed=False, programmatic_value=lambda ctx: len(ctx.data('payload'))),
            {'usage': 'io,doc', 'description': _CHUNK_LENGTH_DESCR},
        )
        payload = (BytesBlock(length=lambda ctx: ctx.data('chunk_length')), {'is_unknown': True})


class NfsuMeshDescriptorChunk(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Mesh descriptor: everything about a single mesh (a car part). Contains the mesh '
            'header chunk, lists of hashes and the mesh data container with vertices and '
            'faces. The converter exports every descriptor as a separate mesh, named after '
            '`mesh_name` of the header',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = (
            IntegerBlock(length=4, is_signed=False, value_validator=Eq(0x80_13_40_10)),
            {'description': _CHUNK_ID_DESCR},
        )
        chunk_length = (
            IntegerBlock(
                length=4,
                is_signed=False,
                programmatic_value=lambda ctx: ctx.block.field_blocks_map['sub_chunks'].estimate_packed_size(
                    ctx.data('sub_chunks')
                ),
            ),
            {'usage': 'io,doc', 'description': _CHUNK_LENGTH_DESCR},
        )
        sub_chunks = (
            ArrayBlock(
                length=lambda ctx: determine_chunks_amount(
                    ctx, read_bytes_remaining_func=lambda ctx: ctx.data('chunk_length')
                ),
                child=DelegateBlock(
                    possible_blocks=[
                        Chunk00134011(),
                        Chunk00134012(),
                        Chunk00134013(),
                        Chunk80134100(),
                        Chunk001340XX(),
                        # UnknownChunk(),
                    ],
                    choice_index=lambda ctx, **_: determine_chunks_class(ctx),
                ),
            ),
            {
                'description': 'Child chunks, read until the payload is exhausted. Block class picked '
                'according to the chunk id'
            },
        )


class Chunk80134001(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'File info container: the first meaningful chunk of the file. Holds file info, '
            'the list of mesh ids and a per-mesh table',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = (
            IntegerBlock(length=4, is_signed=False, value_validator=Eq(0x80_13_40_01)),
            {'description': _CHUNK_ID_DESCR},
        )
        chunk_length = (
            IntegerBlock(
                length=4,
                is_signed=False,
                programmatic_value=lambda ctx: ctx.block.field_blocks_map['sub_chunks'].estimate_packed_size(
                    ctx.data('sub_chunks')
                ),
            ),
            {'usage': 'io,doc', 'description': _CHUNK_LENGTH_DESCR},
        )
        # always 3 or 4 blocks
        sub_chunks = (
            ArrayBlock(
                length=lambda ctx: determine_chunks_amount(
                    ctx, read_bytes_remaining_func=lambda ctx: ctx.data('chunk_length')
                ),
                child=DelegateBlock(
                    possible_blocks=[
                        Chunk00134002(),
                        Chunk00134003(),
                        Chunk001340XX(),
                        Chunk80134008(),
                        # UnknownChunk(),
                    ],
                    choice_index=lambda ctx, **_: determine_chunks_class(ctx),
                ),
            ),
            {
                'description': 'Child chunks (always 3 or 4), read until the payload is exhausted. Block class '
                'picked according to the chunk id'
            },
        )


class Chunk80134020(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {**super().schema, 'block_description': 'Unknown top-level chunk, kept as raw bytes'}

    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = (
            IntegerBlock(length=4, is_signed=False, value_validator=Eq(0x80_13_40_20)),
            {'description': _CHUNK_ID_DESCR},
        )
        chunk_length = (
            IntegerBlock(length=4, is_signed=False, programmatic_value=lambda ctx: len(ctx.data('payload'))),
            {'usage': 'io,doc', 'description': _CHUNK_LENGTH_DESCR},
        )
        payload = (BytesBlock(length=lambda ctx: ctx.data('chunk_length')), {'is_unknown': True})


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
        length = int.from_bytes(ctx.buffer.read(4), byteorder='little', signed=False)
        ctx.buffer.seek(length, SEEK_CUR)
        read_bytes_remaining -= 8 + length
    # return buffer pointer to the original state
    ctx.buffer.seek(buffer_pos)
    return num_chunks


def determine_chunks_class(ctx: ReadContext):
    id = int.from_bytes(ctx.buffer.read(4), byteorder='little', signed=False)
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
    elif id_hex == '00134B02':
        class_name = 'NfsuMeshMaterialsChunk'
    else:
        class_name = 'Chunk' + id_hex
    try:
        return ctx.block.child.get_choice_index_by_class_name(class_name)
    except ValueError:
        raise Exception('Unknown chunk: ' + class_name)
        # return ctx.block.child.get_choice_index_by_class_name('UnknownChunk')


class NfsuBinGeometry(DeclarativeCompoundBlock):
    def __init__(self, whole_file: bool = True, **kwargs):
        # car GEOMETRY.BIN: chunks after the pack (e.g. 0x80034020) are read as its own chunks, until the end of file
        super().__init__(**kwargs)
        self.whole_file = whole_file

    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Geometry pack: car geometry file (GEOMETRY.BIN), also a chunk of track bundles. '
            'A sequence of chunks, each having 32-bit id and 32-bit payload length; chunks with id '
            'starting with 0x80 are containers of other chunks. The pack starts with a file info '
            'container, followed by a mesh descriptor per mesh (car part, scenery object), '
            'interleaved with zero-id padding chunks',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        header = (
            IntegerBlock(length=4, value_validator=Eq(0x80134000)),
            {'description': 'Resource ID (chunk id of the whole file)'},
        )
        data_length = (
            IntegerBlock(
                length=4,
                programmatic_value=lambda ctx: (
                    ctx.data('data_length')
                    if ctx.block.whole_file
                    else ctx.block.field_blocks_map['chunks'].estimate_packed_size(ctx.data('chunks'))
                ),
            ),
            {'description': 'Length of the rest of the chunk in bytes'},
        )
        chunks = (
            ArrayBlock(
                length=(
                    lambda ctx: determine_chunks_amount(
                        ctx,
                        read_bytes_remaining_func=None if ctx.block.whole_file else lambda ctx: ctx.data('data_length'),
                    ),
                    'until the end of chunk (car GEOMETRY.BIN: until the end of file)',
                ),
                child=DelegateBlock(
                    possible_blocks=[
                        ZeroChunk(),
                        NfsuMeshDescriptorChunk(),
                        Chunk80134001(),
                        Chunk80034020(),
                        # UnknownChunk(),
                    ],
                    choice_index=lambda ctx, **_: determine_chunks_class(ctx),
                ),
            ),
            {
                'description': 'Top-level chunks, read until the end of file. Block class picked according to the '
                'chunk id'
            },
        )

    def serializer_class(self):
        from serializers.geometries import NfsuBinGeometrySerializer

        return NfsuBinGeometrySerializer
