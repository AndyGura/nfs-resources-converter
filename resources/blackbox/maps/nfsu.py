from io import SEEK_CUR
from typing import Dict

from library.read_blocks import (
    ArrayBlock,
    BytesBlock,
    DeclarativeCompoundBlock,
    DecimalBlock,
    FixedPointBlock,
    IntegerBlock,
)
from library.read_blocks.misc.value_validators import Eq
from library.read_blocks.strings import UTF8Block
from resources.blackbox.bitmaps.nfsu import NfsuTexturePack
from resources.blackbox.chunks import (
    chunk_delegate,
    container_chunk_length,
    is_name_bytes,
    nfsu_sub_chunks_field,
    peek_chunk_length,
    peek_chunk_payload,
)
from resources.blackbox.geometries.nfsu import (
    _CHUNK_ID_DESCR,
    _CHUNK_LENGTH_DESCR,
    _ELEVENS_DESCR,
    NfsuBinGeometry,
    ZeroChunk,
    determine_chunks_amount,
    elevens_length,
)
from resources.eac.fields.misc import Point3D


class NfsuScenerySectionHeader(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {**super().schema, 'block_description': 'Scenery header: number of the section it belongs to'}

    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = (IntegerBlock(length=4, value_validator=Eq(0x00034101)), {'description': _CHUNK_ID_DESCR})
        chunk_length = (
            IntegerBlock(length=4, programmatic_value=lambda ctx: len(ctx.data('elevens')) + 60),
            {'usage': 'io,doc', 'description': _CHUNK_LENGTH_DESCR},
        )
        elevens = (
            BytesBlock(length=(lambda ctx: elevens_length(ctx), 'up to 16-bytes alignment')),
            {'usage': 'io,doc', 'description': _ELEVENS_DESCR},
        )
        unk0 = (BytesBlock(length=12), {'is_unknown': True})
        section_number = (
            IntegerBlock(length=4),
            {
                'description': 'Number of the section: letter index (A = 1) * 100 + number, e.g. 2617 for "Z17". '
                'Matches `number` in the streaming sections table (without its 0x10000 flag)'
            },
        )
        unk1 = (BytesBlock(length=44), {'is_unknown': True})


class NfsuSceneryInfo(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {**super().schema, 'block_description': 'Scenery object definition: which mesh to draw'}

    class Fields(DeclarativeCompoundBlock.Fields):
        mesh_ids = (
            ArrayBlock(child=IntegerBlock(length=4), length=6),
            {
                'description': 'Mesh ids (hashes of mesh names, `mesh_id` of mesh header chunks). The first one is '
                'the main mesh, others are probably levels of detail'
            },
        )
        far_clip_sizes = (ArrayBlock(child=IntegerBlock(length=2, is_signed=True), length=4), {'is_unknown': True})
        unk0 = (IntegerBlock(length=4), {'is_unknown': True})
        model_pointers = (
            ArrayBlock(child=IntegerBlock(length=4), length=6),
            {'description': 'Filled by the game in runtime', 'is_unknown': True},
        )
        facade_flags = (BytesBlock(length=6), {'is_unknown': True})
        unk1 = (IntegerBlock(length=2), {'is_unknown': True})
        radius = (DecimalBlock(length=4), {'description': 'Bounding sphere radius'})


class NfsuSceneryInfos(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {**super().schema, 'block_description': 'Scenery object definitions'}

    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = (IntegerBlock(length=4, value_validator=Eq(0x00034102)), {'description': _CHUNK_ID_DESCR})
        chunk_length = (
            IntegerBlock(length=4, programmatic_value=lambda ctx: len(ctx.data('infos')) * 72),
            {'usage': 'io,doc', 'description': _CHUNK_LENGTH_DESCR},
        )
        infos = (
            ArrayBlock(child=NfsuSceneryInfo(), length=lambda ctx: ctx.data('chunk_length') // 72),
            {'description': 'Definitions'},
        )


class NfsuSceneryInstance(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {**super().schema, 'block_description': 'Placed scenery object'}

    class Fields(DeclarativeCompoundBlock.Fields):
        bounding_box_min = (
            Point3D(child=IntegerBlock(length=2, is_signed=True)),
            {'description': 'Minimum corner of the bounding box in world coordinates'},
        )
        bounding_box_max = (
            Point3D(child=IntegerBlock(length=2, is_signed=True)),
            {'description': 'Maximum corner of the bounding box in world coordinates'},
        )
        info_index = (IntegerBlock(length=2), {'description': 'Index of the object definition in this scenery'})
        exclude_flags = (IntegerBlock(length=2), {'is_unknown': True})
        position = (Point3D(child=DecimalBlock(length=4)), {'description': 'Position in world coordinates'})
        rotation = (
            ArrayBlock(child=FixedPointBlock(length=2, fraction_bits=13, is_signed=True), length=9),
            {
                'description': 'Rotation and scale matrix 3x3, row by row. World position of a mesh vertex v is '
                'v.x * row0 + v.y * row1 + v.z * row2 + position'
            },
        )
        padding = (IntegerBlock(length=2), {'is_unknown': True})


class NfsuSceneryInstances(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {**super().schema, 'block_description': 'Placed scenery objects'}

    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = (IntegerBlock(length=4, value_validator=Eq(0x00034103)), {'description': _CHUNK_ID_DESCR})
        chunk_length = (
            IntegerBlock(
                length=4, programmatic_value=lambda ctx: len(ctx.data('elevens')) + len(ctx.data('instances')) * 48
            ),
            {'usage': 'io,doc', 'description': _CHUNK_LENGTH_DESCR},
        )
        elevens = (
            BytesBlock(length=(lambda ctx: elevens_length(ctx), 'up to 16-bytes alignment')),
            {'usage': 'io,doc', 'description': _ELEVENS_DESCR},
        )
        instances = (
            ArrayBlock(
                child=NfsuSceneryInstance(),
                length=lambda ctx: (ctx.data('chunk_length') - len(ctx.data('elevens'))) // 48,
            ),
            {'description': 'Instances'},
        )


class NfsuScenery(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Scenery of a section: object definitions referencing meshes by id, and their '
            'placements in the world',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = (IntegerBlock(length=4, value_validator=Eq(0x80034100)), {'description': _CHUNK_ID_DESCR})
        chunk_length = container_chunk_length()
        sub_chunks = nfsu_sub_chunks_field(
            [NfsuScenerySectionHeader(), NfsuSceneryInfos(), NfsuSceneryInstances(), ZeroChunk()],
            'Header, definitions, instances and an unknown chunk 0x00034104',
        )


def _nfsu2_scenery_info_names_ok(infos_payload: bytes) -> bool:
    return (
        len(infos_payload) % 68 == 0
        and len(infos_payload) > 0
        and all(is_name_bytes(infos_payload[i : i + 32]) for i in range(0, len(infos_payload), 68))
    )


class Nfsu2SceneryInfo(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {**super().schema, 'block_description': 'NFSU2 scenery object definition: which mesh to draw'}

    class Fields(DeclarativeCompoundBlock.Fields):
        name = (UTF8Block(length=32), {'description': 'Object name, e.g. "SKYDOME"'})
        mesh_ids = (
            ArrayBlock(child=IntegerBlock(length=4), length=3),
            {
                'description': 'Mesh ids (hashes of mesh names, `mesh_id` of mesh header chunks). The first one is '
                'the main mesh, others are probably levels of detail'
            },
        )
        flags = (ArrayBlock(child=IntegerBlock(length=2), length=2), {'is_unknown': True})
        model_pointers = (
            ArrayBlock(child=IntegerBlock(length=4), length=3),
            {'description': 'Filled by the game in runtime', 'is_unknown': True},
        )
        radius = (DecimalBlock(length=4), {'description': 'Bounding sphere radius'})
        hierarchy_key = (IntegerBlock(length=4), {'is_unknown': True})


class Nfsu2SceneryInfos(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {**super().schema, 'block_description': 'NFSU2 scenery object definitions'}

    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = (IntegerBlock(length=4, value_validator=Eq(0x00034102)), {'description': _CHUNK_ID_DESCR})
        chunk_length = (
            IntegerBlock(length=4, programmatic_value=lambda ctx: len(ctx.data('infos')) * 68),
            {'usage': 'io,doc', 'description': _CHUNK_LENGTH_DESCR},
        )
        infos = (
            ArrayBlock(child=Nfsu2SceneryInfo(), length=lambda ctx: ctx.data('chunk_length') // 68),
            {'description': 'Definitions'},
        )


class Nfsu2SceneryInstance(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {**super().schema, 'block_description': 'NFSU2 placed scenery object'}

    class Fields(DeclarativeCompoundBlock.Fields):
        bounding_box_min = (
            Point3D(child=DecimalBlock(length=4)),
            {'description': 'Minimum corner of the bounding box in world coordinates'},
        )
        bounding_box_max = (
            Point3D(child=DecimalBlock(length=4)),
            {'description': 'Maximum corner of the bounding box in world coordinates'},
        )
        info_index = (IntegerBlock(length=2), {'description': 'Index of the object definition in this scenery'})
        instance_flags = (IntegerBlock(length=2), {'is_unknown': True})
        preculler_info_index = (IntegerBlock(length=4, is_signed=True), {'is_unknown': True})
        position = (Point3D(child=DecimalBlock(length=4)), {'description': 'Position in world coordinates'})
        rotation = (
            ArrayBlock(child=FixedPointBlock(length=2, fraction_bits=13, is_signed=True), length=9),
            {
                'description': 'Rotation and scale matrix 3x3, row by row. World position of a mesh vertex v is '
                'v.x * row0 + v.y * row1 + v.z * row2 + position'
            },
        )
        padding = (IntegerBlock(length=2), {'is_unknown': True})


class Nfsu2SceneryInstances(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {**super().schema, 'block_description': 'NFSU2 placed scenery objects'}

    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = (IntegerBlock(length=4, value_validator=Eq(0x00034103)), {'description': _CHUNK_ID_DESCR})
        chunk_length = (
            IntegerBlock(
                length=4, programmatic_value=lambda ctx: len(ctx.data('elevens')) + len(ctx.data('instances')) * 64
            ),
            {'usage': 'io,doc', 'description': _CHUNK_LENGTH_DESCR},
        )
        elevens = (
            BytesBlock(length=(lambda ctx: elevens_length(ctx), 'up to 16-bytes alignment')),
            {'usage': 'io,doc', 'description': _ELEVENS_DESCR},
        )
        instances = (
            ArrayBlock(
                child=Nfsu2SceneryInstance(),
                length=lambda ctx: (ctx.data('chunk_length') - len(ctx.data('elevens'))) // 64,
            ),
            {'description': 'Instances'},
        )


class Nfsu2Scenery(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'NFSU2 scenery of a section: same as in NFSU, with bigger object definitions '
            '(named) and instances (float bounding box). Told apart from NFSU scenery by the definitions: '
            'every NFSU2 one starts with a name',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = (IntegerBlock(length=4, value_validator=Eq(0x80034100)), {'description': _CHUNK_ID_DESCR})
        chunk_length = container_chunk_length()
        sub_chunks = nfsu_sub_chunks_field(
            [NfsuScenerySectionHeader(), Nfsu2SceneryInfos(), Nfsu2SceneryInstances(), ZeroChunk()],
            'Header, definitions, instances and unknown chunks 0x00034104, 0x00034105, 0x00034106',
        )

    def matches_chunk(self, ctx) -> bool:
        payload = peek_chunk_payload(ctx, peek_chunk_length(ctx))
        pos = 0
        while pos + 8 <= len(payload):
            chunk_id = int.from_bytes(payload[pos : pos + 4], 'little')
            chunk_length = int.from_bytes(payload[pos + 4 : pos + 8], 'little')
            if chunk_id == 0x00034102:
                return _nfsu2_scenery_info_names_ok(payload[pos + 8 : pos + 8 + chunk_length])
            pos += 8 + chunk_length
        return False


def _nfsmw_scenery_info_names_ok(infos_payload: bytes) -> bool:
    return (
        len(infos_payload) % 72 == 0
        and len(infos_payload) > 0
        and all(is_name_bytes(infos_payload[i : i + 24]) for i in range(0, len(infos_payload), 72))
        and not _nfsu2_scenery_info_names_ok(infos_payload)
    )


class NfsmwSceneryInfo(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {**super().schema, 'block_description': 'NFSMW scenery object definition: which mesh to draw'}

    class Fields(DeclarativeCompoundBlock.Fields):
        name = (UTF8Block(length=24), {'description': 'Object name, e.g. "XO_StreetLightCb_1b_00"'})
        mesh_ids = (
            ArrayBlock(child=IntegerBlock(length=4), length=4),
            {
                'description': 'Mesh ids (hashes of mesh names, `mesh_id` of mesh header chunks). The first one is '
                'the main mesh, others are probably levels of detail'
            },
        )
        model_pointers = (
            ArrayBlock(child=IntegerBlock(length=4), length=4),
            {'description': 'Filled by the game in runtime', 'is_unknown': True},
        )
        radius = (DecimalBlock(length=4), {'description': 'Bounding sphere radius'})
        mesh_checksum = (IntegerBlock(length=4), {'is_unknown': True})
        hierarchy_name_hash = (IntegerBlock(length=4), {'is_unknown': True})
        hierarchy_pointer = (
            IntegerBlock(length=4),
            {'description': 'Filled by the game in runtime', 'is_unknown': True},
        )


class NfsmwSceneryInfos(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {**super().schema, 'block_description': 'NFSMW scenery object definitions'}

    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = (IntegerBlock(length=4, value_validator=Eq(0x00034102)), {'description': _CHUNK_ID_DESCR})
        chunk_length = (
            IntegerBlock(length=4, programmatic_value=lambda ctx: len(ctx.data('infos')) * 72),
            {'usage': 'io,doc', 'description': _CHUNK_LENGTH_DESCR},
        )
        infos = (
            ArrayBlock(child=NfsmwSceneryInfo(), length=lambda ctx: ctx.data('chunk_length') // 72),
            {'description': 'Definitions'},
        )


class NfsmwSceneryInstance(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {**super().schema, 'block_description': 'NFSMW placed scenery object'}

    class Fields(DeclarativeCompoundBlock.Fields):
        bounding_box_min = (
            Point3D(child=DecimalBlock(length=4)),
            {'description': 'Minimum corner of the bounding box in world coordinates'},
        )
        bounding_box_max = (
            Point3D(child=DecimalBlock(length=4)),
            {'description': 'Maximum corner of the bounding box in world coordinates'},
        )
        exclude_flags = (IntegerBlock(length=4), {'is_unknown': True})
        preculler_info_index = (IntegerBlock(length=2, is_signed=True), {'is_unknown': True})
        lighting_context_number = (IntegerBlock(length=2, is_signed=True), {'is_unknown': True})
        position = (Point3D(child=DecimalBlock(length=4)), {'description': 'Position in world coordinates'})
        rotation = (
            ArrayBlock(child=FixedPointBlock(length=2, fraction_bits=13, is_signed=True), length=9),
            {
                'description': 'Rotation and scale matrix 3x3, row by row. World position of a mesh vertex v is '
                'v.x * row0 + v.y * row1 + v.z * row2 + position'
            },
        )
        info_index = (IntegerBlock(length=2), {'description': 'Index of the object definition in this scenery'})


class NfsmwSceneryInstances(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {**super().schema, 'block_description': 'NFSMW placed scenery objects'}

    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = (IntegerBlock(length=4, value_validator=Eq(0x00034103)), {'description': _CHUNK_ID_DESCR})
        chunk_length = (
            IntegerBlock(
                length=4, programmatic_value=lambda ctx: len(ctx.data('elevens')) + len(ctx.data('instances')) * 64
            ),
            {'usage': 'io,doc', 'description': _CHUNK_LENGTH_DESCR},
        )
        elevens = (
            BytesBlock(length=(lambda ctx: elevens_length(ctx), 'up to 16-bytes alignment')),
            {'usage': 'io,doc', 'description': _ELEVENS_DESCR},
        )
        instances = (
            ArrayBlock(
                child=NfsmwSceneryInstance(),
                length=lambda ctx: (ctx.data('chunk_length') - len(ctx.data('elevens'))) // 64,
            ),
            {'description': 'Instances'},
        )


class NfsmwScenery(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'NFSMW scenery of a section: object definitions (named, 4 mesh ids) and their '
            'placements in the world. Told apart from NFSU and NFSU2 scenery by the definitions: every one starts '
            'with a 24-byte name',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = (IntegerBlock(length=4, value_validator=Eq(0x80034100)), {'description': _CHUNK_ID_DESCR})
        chunk_length = container_chunk_length()
        sub_chunks = nfsu_sub_chunks_field(
            [NfsuScenerySectionHeader(), NfsmwSceneryInfos(), NfsmwSceneryInstances(), ZeroChunk()],
            'Header, instances, definitions and unknown chunks 0x00034105, 0x00034106, 0x00034107',
        )

    def matches_chunk(self, ctx) -> bool:
        payload = peek_chunk_payload(ctx, peek_chunk_length(ctx))
        pos = 0
        while pos + 8 <= len(payload):
            chunk_id = int.from_bytes(payload[pos : pos + 4], 'little')
            chunk_length = int.from_bytes(payload[pos + 4 : pos + 8], 'little')
            if chunk_id == 0x00034102:
                return _nfsmw_scenery_info_names_ok(payload[pos + 8 : pos + 8 + chunk_length])
            pos += 8 + chunk_length
        return False


class NfsuStreamingSection(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {**super().schema, 'block_description': 'Location of a streamed section in the STREAM*.BUN file'}

    class Fields(DeclarativeCompoundBlock.Fields):
        name = (UTF8Block(length=8), {'description': 'Section name, e.g. "A37"'})
        number = (
            IntegerBlock(length=4),
            {'description': 'Section number: letter index (A = 1) * 100 + number. Some have flag 0x10000 set'},
        )
        unk0 = (IntegerBlock(length=4), {'is_unknown': True})
        unk1 = (IntegerBlock(length=4), {'is_unknown': True})
        offset = (IntegerBlock(length=4), {'description': 'Offset of the section in the stream file'})
        size = (IntegerBlock(length=4), {'description': 'Size of the section in the stream file'})
        size2 = (
            IntegerBlock(length=4),
            {'description': 'Equals to `size` unless the section has textures, then a bit smaller', 'is_unknown': True},
        )
        hash = (IntegerBlock(length=4), {'is_unknown': True})
        unk2 = (BytesBlock(length=20), {'is_unknown': True})


class NfsuStreamingSections(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Table of streamed sections: where the world sections of the race lie in the '
            'STREAM*.BUN file. NFSU2 has another chunk with this id',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = (IntegerBlock(length=4, value_validator=Eq(0x00034107)), {'description': _CHUNK_ID_DESCR})
        chunk_length = (
            IntegerBlock(length=4, programmatic_value=lambda ctx: len(ctx.data('sections')) * 56),
            {'usage': 'io,doc', 'description': _CHUNK_LENGTH_DESCR},
        )
        sections = (
            ArrayBlock(child=NfsuStreamingSection(), length=lambda ctx: ctx.data('chunk_length') // 56),
            {'description': 'Sections'},
        )

    def matches_chunk(self, ctx) -> bool:
        # NFSU2 has another chunk with this id (8-byte records), its sections table is chunk 0x00034110
        if peek_chunk_length(ctx) % 56:
            return False
        name = peek_chunk_payload(ctx, 8)
        return len(name) == 8 and name[0] != 0 and is_name_bytes(name)


class Nfsu2StreamingSection(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {**super().schema, 'block_description': 'NFSU2: location of a streamed section in the STREAM*.BUN file'}

    class Fields(DeclarativeCompoundBlock.Fields):
        name = (UTF8Block(length=8), {'description': 'Section name, e.g. "A37"'})
        number = (
            IntegerBlock(length=4),
            {'description': 'Section number: letter index (A = 1) * 100 + number'},
        )
        unk0 = (IntegerBlock(length=4), {'is_unknown': True})
        unk1 = (IntegerBlock(length=4), {'description': '1, except the first section "--"', 'is_unknown': True})
        offset = (IntegerBlock(length=4), {'description': 'Offset of the section in the stream file'})
        size = (
            IntegerBlock(length=4),
            {'description': 'Size of the section in the stream file, without padding to 2048 bytes'},
        )
        size2 = (
            IntegerBlock(length=4),
            {'description': 'Equals to `size` unless the section has textures, then smaller', 'is_unknown': True},
        )
        unk2 = (
            IntegerBlock(length=4),
            {'description': 'Section number + 10000 or 20000 (or 20000 for "--")', 'is_unknown': True},
        )
        center = (
            ArrayBlock(child=DecimalBlock(length=4), length=2),
            {'description': 'Presumably the center of the section (X, Y) in world coordinates', 'is_unknown': True},
        )
        radius = (DecimalBlock(length=4), {'description': 'Presumably radius of the section', 'is_unknown': True})
        hash = (IntegerBlock(length=4), {'is_unknown': True})
        unk3 = (BytesBlock(length=28), {'is_unknown': True})


class Nfsu2StreamingSections(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'NFSU2 table of streamed sections: where the world sections of the location lie '
            'in the STREAM*.BUN file',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = (IntegerBlock(length=4, value_validator=Eq(0x00034110)), {'description': _CHUNK_ID_DESCR})
        chunk_length = (
            IntegerBlock(length=4, programmatic_value=lambda ctx: len(ctx.data('sections')) * 80),
            {'usage': 'io,doc', 'description': _CHUNK_LENGTH_DESCR},
        )
        sections = (
            ArrayBlock(child=Nfsu2StreamingSection(), length=lambda ctx: ctx.data('chunk_length') // 80),
            {'description': 'Sections'},
        )


def _section_names_ok(ctx, record_size: int) -> bool:
    length = peek_chunk_length(ctx)
    if length == 0 or length % record_size:
        return False
    payload = peek_chunk_payload(ctx, length)
    return all(is_name_bytes(payload[i : i + 8]) for i in range(0, length, record_size))


class NfsmwStreamingSection(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {**super().schema, 'block_description': 'NFSMW: location of a streamed section in the STREAM*.BUN file'}

    class Fields(DeclarativeCompoundBlock.Fields):
        name = (UTF8Block(length=8), {'description': 'Section name, e.g. "T26"'})
        number = (IntegerBlock(length=4), {'description': 'Section number: letter index (A = 1) * 100 + number'})
        unk0 = (IntegerBlock(length=4), {'is_unknown': True})
        unk1 = (IntegerBlock(length=4), {'description': 'Always 1', 'is_unknown': True})
        offset = (IntegerBlock(length=4), {'description': 'Offset of the section in the stream file'})
        size = (
            IntegerBlock(length=4),
            {'description': 'Size of the section in the stream file, without padding to 2048 bytes'},
        )
        size2 = (IntegerBlock(length=4), {'description': 'Always equals to `size`', 'is_unknown': True})
        size3 = (
            IntegerBlock(length=4),
            {'description': 'Equals to `size` unless the section has textures, then smaller', 'is_unknown': True},
        )
        unk2 = (
            IntegerBlock(length=4),
            {'description': 'Section number + 2000, 4000 ... 22000 (10, 20, 30 for X0, Z0, Y0)', 'is_unknown': True},
        )
        center = (
            ArrayBlock(child=DecimalBlock(length=4), length=2),
            {'description': 'Presumably the center of the section (X, Y) in world coordinates', 'is_unknown': True},
        )
        radius = (DecimalBlock(length=4), {'description': 'Presumably radius of the section', 'is_unknown': True})
        hash = (IntegerBlock(length=4), {'is_unknown': True})
        unk3 = (BytesBlock(length=36), {'is_unknown': True})


class NfsmwStreamingSections(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'NFSMW table of streamed sections: where the world sections of the location lie '
            'in the STREAM*.BUN file',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = (IntegerBlock(length=4, value_validator=Eq(0x00034110)), {'description': _CHUNK_ID_DESCR})
        chunk_length = (
            IntegerBlock(length=4, programmatic_value=lambda ctx: len(ctx.data('sections')) * 92),
            {'usage': 'io,doc', 'description': _CHUNK_LENGTH_DESCR},
        )
        sections = (
            ArrayBlock(child=NfsmwStreamingSection(), length=lambda ctx: ctx.data('chunk_length') // 92),
            {'description': 'Sections'},
        )

    def matches_chunk(self, ctx) -> bool:
        return _section_names_ok(ctx, 92) and not _section_names_ok(ctx, 80)


NFSU_BUNDLE_CHUNK_BLOCKS = [
    ZeroChunk(),
    NfsuBinGeometry(whole_file=False),
    NfsuTexturePack(),
    NfsmwScenery(),
    Nfsu2Scenery(),
    NfsuScenery(),
    NfsuStreamingSections(),
    NfsmwStreamingSections(),
    Nfsu2StreamingSections(),
]


def _bundle_chunks_amount(ctx):
    return determine_chunks_amount(ctx)


class NfsuChunkBundle(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Chunk bundle (*.BUN, *.BIN, uncompressed *.lzc): a sequence of chunks, each '
            'having 32-bit id, 32-bit payload length and payload; chunks with the highest bit '
            'of id set are containers of other chunks. Geometry packs, texture packs, scenery '
            'and streaming sections table are decoded, other chunks are kept as raw bytes',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        chunks = (
            ArrayBlock(
                length=(lambda ctx: _bundle_chunks_amount(ctx), 'until the end of file'),
                child=chunk_delegate(NFSU_BUNDLE_CHUNK_BLOCKS),
            ),
            {'description': 'Chunks'},
        )


class NfsuTrackBundle(NfsuChunkBundle):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Race bundle (NFSU TRACKS/TRACKBnnnn.lzc, uncompressed) or location bundle (NFSU2 '
            'TRACKS/L4RA.BUN, NFSMW TRACKS/L2RA.BUN): a chunk bundle with the streaming sections table of the world, which is stored in '
            'TRACKS/STREAM*.BUN. ' + super().schema['block_description'],
        }

    def serializer_class(self):
        from serializers.maps import NfsuTrackBundleSerializer

        return NfsuTrackBundleSerializer


def walk_nfsu_chunk_ids(buffer, length: int):
    """Ids of top-level chunks if the buffer is a chunk bundle (chunk lengths add up to the given length exactly),
    else None. Buffer position is not changed"""
    pos = buffer.tell()
    ids = []
    try:
        remaining = length
        while remaining > 0:
            header = buffer.read(8)
            if len(header) < 8:
                return None
            chunk_id = int.from_bytes(header[:4], 'little')
            chunk_length = int.from_bytes(header[4:], 'little')
            remaining -= 8 + chunk_length
            if remaining < 0:
                return None
            ids.append(chunk_id)
            buffer.seek(chunk_length, SEEK_CUR)
        return ids
    finally:
        buffer.seek(pos)
