from library.context import ReadContext
from library.read_blocks import (DeclarativeCompoundBlock,
                                 IntegerBlock, BytesBlock, ArrayBlock, CompoundBlock,
                                 )
from library.read_blocks.misc.optional import OptionalBlock
from library.read_blocks.misc.value_validators import Eq


# https://gemini.google.com/app/3ef110c2ec060523
# [0x80134000] Master Container (5,761,160 bytes)
#  ├── [8 Bytes Padding]
#  ├── [0x80134001] Sub-Container (11,220 bytes)
#  │    ├── [0x00134002] Info Block (128 bytes)
#  │    ├── [0x00134003] Geometry Data Block (3,160 bytes)
#  │    ├── [0x00134004] Material Table Block (7,900 bytes)
#  │    └── [0x80134008] Container Closer Marker (0 bytes)
#  ├── [0x00000000] Alignment Padding Block (12 bytes)
#  └── [0x80134010] Master Mesh Container (15,108 bytes)
#       ├── [0x00134011] Mesh Descriptor Block (176 bytes)
#       ├── [0x00134012] Vertex Buffer Pointer (8 bytes)
#       ├── [0x00134013] Index Buffer Pointer (8 bytes)
#       ├── [0x80134100] Mesh Part Closer (11,008 bytes)
#       ├── [0x00134017] Mesh Properties Block (12 bytes)
#       ├── [0x00134018] Stream Definition Block (1,536 bytes)
#       └── [0x00134019] Stream Allocation Block (2,304 bytes)

class NfsuGeometryInfoBlock(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = IntegerBlock(length=4)  # 0x00134001
        chunk_length = IntegerBlock(length=4)  # Length of metadata payload
        payload = BytesBlock(length=lambda ctx: ctx.data('chunk_length'))


class NfsuCarPartMesh(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        # Every individual part (e.g., FRONT_BUMPER) starts with its own header layout
        part_id = IntegerBlock(length=4)  # Usually sub-ids like 0x00134011, etc.
        part_length = IntegerBlock(length=4)
        part_data = BytesBlock(length=lambda ctx: ctx.data('part_length'))


class NfsuPartsContainer(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = IntegerBlock(length=4)  # 0x80134002
        chunk_length = IntegerBlock(length=4)

        # Since this container holds multiple parts until its chunk_length is exhausted,
        # we can consume its payload bytes directly, or loop through its nested chunks.
        container_payload = BytesBlock(length=lambda ctx: ctx.data('chunk_length'))


class NfsuGeometryContainer(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = IntegerBlock(length=4)  # This will match 0x80134001
        chunk_length = IntegerBlock(length=4)  # The length of everything inside this container

        # Since this is a massive wrapper, we read its inner contents
        payload = BytesBlock(length=lambda ctx: ctx.data('chunk_length'))


class NfsuGeometryHeaderInfo(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = IntegerBlock(length=4)  # This matches 0x80134001
        chunk_length = IntegerBlock(length=4)  # Length of this info payload
        payload = BytesBlock(length=lambda ctx: ctx.data('chunk_length'))


class NfsuInfoBlock(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = IntegerBlock(length=4)  # Matches 1261570 (0x00134002)
        chunk_length = IntegerBlock(length=4)  # Matches 128
        payload = BytesBlock(length=lambda ctx: ctx.data('chunk_length'))


class NfsuGeometryDataBlock(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = IntegerBlock(length=4)  # Matches 0x00134003
        chunk_length = IntegerBlock(length=4)  # Length of the mesh data payload
        payload = BytesBlock(length=lambda ctx: ctx.data('chunk_length'))


class NfsuMaterialTableBlock(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = IntegerBlock(length=4)  # Matches 0x00134004
        chunk_length = IntegerBlock(length=4)  # Length of the material/object table
        payload = BytesBlock(length=lambda ctx: ctx.data('chunk_length'))


class NfsuSubContainer(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = IntegerBlock(length=4, value_validator=Eq(0x80134001))
        chunk_length = IntegerBlock(length=4)  # 11220

        info_block = NfsuInfoBlock()

        # 2. Geometry Mesh Block
        geometry_data = NfsuGeometryDataBlock()

        # 3. Material/Object Table Block (Starts with 0x00134004)
        material_table = NfsuMaterialTableBlock()

        # 4. Recalculate remaining space in this sub-container
        container_remaining = BytesBlock(length=lambda ctx: (
                ctx.data('chunk_length')
                - 8 - ctx.data('info_block/chunk_length')
                - 8 - ctx.data('geometry_data/chunk_length')
                - 8 - ctx.data('material_table/chunk_length')
        ))


class NfsuGenericChunk(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = IntegerBlock(length=4)
        chunk_length = IntegerBlock(length=4)
        payload = BytesBlock(length=lambda ctx: ctx.data('chunk_length'))


class NfsuMeshDescriptorBlock(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = IntegerBlock(length=4)  # Matches 0x00134011
        chunk_length = IntegerBlock(length=4)  # Size of this descriptor payload
        payload = BytesBlock(length=lambda ctx: ctx.data('chunk_length'))


class NfsuVertexBufferBlock(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = IntegerBlock(length=4)  # 0x00134012
        chunk_length = IntegerBlock(length=4)  # 8

        payload = BytesBlock(length=lambda ctx: ctx.data('chunk_length'))
        # Unpacking the reference data
        # vertex_stream_hash = IntegerBlock(length=4) # Matches 0x721AFF7C (Little-Endian)
        # stream_offset = IntegerBlock(length=4)      # Matches 0


class NfsuIndexBufferBlock(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = IntegerBlock(length=4)  # 0x00134013
        chunk_length = IntegerBlock(length=4)  # 8

        payload = BytesBlock(length=lambda ctx: ctx.data('chunk_length'))
        # index_stream_hash = IntegerBlock(length=4)  # Matches 0x721AFDDC
        # stream_offset = IntegerBlock(length=4)      # Matches 0


class NfsuMeshPartCloser(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = IntegerBlock(length=4)  # Matches 0x80134100
        chunk_length = IntegerBlock(length=4)  # Total size of the closer data
        payload = BytesBlock(length=lambda ctx: ctx.data('chunk_length'))


class NfsuMeshPropertiesBlock(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = IntegerBlock(length=4)  # 0x00134017
        chunk_length = IntegerBlock(length=4)  # 12
        payload = BytesBlock(length=lambda ctx: ctx.data('chunk_length'))  # 12 bytes of zeros


class NfsuStreamDefinitionBlock(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = IntegerBlock(length=4)  # Matches 0x00134018
        chunk_length = IntegerBlock(length=4)  # Size of the layout definitions
        payload = BytesBlock(length=lambda ctx: ctx.data('chunk_length'))


class NfsuStreamAllocationBlock(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = IntegerBlock(length=4)  # Matches 0x00134019
        chunk_length = IntegerBlock(length=4)  # Size of allocation header
        payload = BytesBlock(length=lambda ctx: ctx.data('chunk_length'))


class UnkBlock(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = IntegerBlock(length=4)
        chunk_length = IntegerBlock(length=4)
        payload = BytesBlock(length=lambda ctx: ctx.data('chunk_length'))


class NfsuMeshContainer(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        chunk_id = IntegerBlock(length=4, value_validator=Eq(0x80134010))  # 0x80134010
        chunk_length = IntegerBlock(length=4, is_signed=False)  # 15108

        mesh_descriptor = NfsuMeshDescriptorBlock()
        vertex_buffer = NfsuVertexBufferBlock()
        index_buffer = NfsuIndexBufferBlock()
        part_closer = NfsuMeshPartCloser()
        mesh_properties = OptionalBlock(child=NfsuMeshPropertiesBlock(),
                                        criteria=lambda ctx: ctx.local_buffer_pos < ctx.data('chunk_length'))
        stream_definition = OptionalBlock(NfsuStreamDefinitionBlock(),
                                          criteria=lambda ctx: ctx.local_buffer_pos < ctx.data(
                                              'chunk_length'))  # 1536 bytes

        # 7. Stream Allocation Block (Starts with 0x00134019)
        stream_allocation = OptionalBlock(child=NfsuStreamAllocationBlock(),
                                          criteria=lambda ctx: ctx.local_buffer_pos < ctx.data('chunk_length'))
        unk_0 = OptionalBlock(child=UnkBlock(),
                            criteria=lambda ctx: ctx.local_buffer_pos < ctx.data('chunk_length'))

        # 8. Recalculate remaining space
        container_remaining = BytesBlock(length=lambda ctx: (
                ctx.data('chunk_length')
                - 8 - ctx.data('mesh_descriptor/chunk_length')
                - 8 - ctx.data('vertex_buffer/chunk_length')
                - 8 - ctx.data('index_buffer/chunk_length')
                - 8 - ctx.data('part_closer/chunk_length')
                - (8 + ctx.data('mesh_properties/chunk_length') if ctx.data('mesh_properties/chunk_id') != 0 else 0)
                - (8 + ctx.data('stream_definition/chunk_length') if ctx.data('stream_definition/chunk_id') != 0 else 0)
                - (8 + ctx.data('stream_allocation/chunk_length') if ctx.data('stream_allocation/chunk_id') != 0 else 0)
                - (8 + ctx.data('unk_0/chunk_length') if ctx.data('unk_0/chunk_id') != 0 else 0)
        ))

    def read(self, ctx: ReadContext, name: str = '', read_bytes_amount=None):
        data = super().read(ctx, name, read_bytes_amount)
        assert len(data['container_remaining']) == 0, ctx.ctx_path
        return data


class NfsuBinGeometry(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        header = IntegerBlock(length=4, value_validator=Eq(0x80134000))
        data_length = IntegerBlock(length=4)
        padding_gap = BytesBlock(length=8)

        first_sub_container = NfsuSubContainer()

        # 2. To handle the rest of the file dynamically, we can loop through
        # the remaining chunks inside the master payload using an ArrayBlock or sequential parsing.
        # For now, let's capture the 20-byte alignment block you just found:

        # Next chunk seems to start without alignment_chunk
        mesh_chunks = ArrayBlock(length=87,
                                 child=CompoundBlock(
                                     fields=[('alignment_chunk', NfsuGenericChunk(), {}),
                                             ('mesh_chunk', NfsuMeshContainer(), {})]))

        # The rest of the file data
        raw_data = BytesBlock(length=lambda ctx: ctx.data('data_length') - ctx.local_buffer_pos)
        extra = BytesBlock(length=lambda ctx: ctx.read_bytes_remaining)

    def read(self, ctx: ReadContext, name: str = '', read_bytes_amount=None):
        data = super().read(ctx, name, read_bytes_amount)
        return data
