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
from resources.blackbox.chunks import chunk_delegate, container_chunk_length, nfsu_sub_chunks_field
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
            'STREAM*.BUN file',
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


NFSU_BUNDLE_CHUNK_BLOCKS = [
    ZeroChunk(),
    NfsuBinGeometry(whole_file=False),
    NfsuTexturePack(),
    NfsuScenery(),
    NfsuStreamingSections(),
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
            'block_description': 'Race bundle (TRACKS/TRACKBnnnn.lzc, uncompressed): a chunk bundle with the '
            'streaming sections table of the race world, which is stored in TRACKS/STREAM*.BUN. '
            + super().schema['block_description'],
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
