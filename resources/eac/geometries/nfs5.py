from os import SEEK_CUR
from typing import Dict

from library.context import ReadContext, WriteContext
from library.exceptions import BlockDefinitionException
from library.read_blocks import (DeclarativeCompoundBlock,
                                 UTF8Block,
                                 IntegerBlock,
                                 ArrayBlock,
                                 BytesBlock,
                                 DelegateBlock, DecimalBlock)
from library.read_blocks.misc.value_validators import Eq, Or
from library.read_blocks.strings import NullTerminatedUTF8Block
from resources.eac.archives.shpi_block import ShpiBlock
from resources.eac.fields.misc import Point3D


class CrpPartInfo1(IntegerBlock):
    @property
    def schema(self):
        return {
            **super().schema,
            'block_description': 'Part info type 1: [dddd_aaaa_aaaa_llll]'
                                 '<br/>d - Damage switch (0x8 means damaged)'
                                 '<br/>a - animation index'
                                 '<br/>l - Level of detail',
        }

    def __init__(self, **kwargs):
        super().__init__(length=2, is_signed=False, **kwargs)

    def read(self, ctx: ReadContext, name: str = '', read_bytes_amount=None):
        data = super().read(ctx, name, read_bytes_amount)
        return {
            'damage': data >> 12,
            'animation_index': (data >> 4) & 0xff,
            'lod': data & 0xf,
        }

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        value = (data['damage'] & 0xf) << 12
        value = value | ((data['animation_index'] & 0xff) << 4)
        value = value | (data['lod'] & 0xf)
        return super().write(value, ctx, name)


class CrpPartInfo2(IntegerBlock):
    @property
    def schema(self):
        return {
            **super().schema,
            'block_description': 'Part info type 2: [llll_uuuu_uuuu_pppp]'
                                 '<br/>l - Level of detail'
                                 '<br/>u - unknown'
                                 '<br/>p - part index',
        }

    def __init__(self, **kwargs):
        super().__init__(length=2, is_signed=False, **kwargs)

    def read(self, ctx: ReadContext, name: str = '', read_bytes_amount=None):
        data = super().read(ctx, name, read_bytes_amount)
        return {
            'lod': data >> 12,
            'unk': (data >> 4) & 0xff,
            'part_index': data & 0xf,
        }

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        value = (data['lod'] & 0xf) << 12
        value = value | ((data['unk'] & 0xff) << 4)
        value = value | (data['part_index'] & 0xf)
        return super().write(value, ctx, name)


class UnkPart2(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {**super().schema,
                'block_description': 'Unknown part with index and 2-chars identifier'}

    class Fields(DeclarativeCompoundBlock.Fields):
        idx = (IntegerBlock(length=2),
               {'description': 'A part index of the same identifier (in the same article)'})
        identifier = (
            UTF8Block(length=2, value_validator=Or(['zd', 'ns', 'fd'])),
            {'description': 'Identifier'})
        unk0 = (IntegerBlock(length=1),
                {'is_unknown': True})
        len = (IntegerBlock(length=3),
               {'description': 'Data length in bytes'})
        unk1 = (IntegerBlock(length=4),
                {'is_unknown': True})
        offset = (IntegerBlock(length=4),
                  {'usage': 'io,doc',
                   'description': 'Data offset (Relative from current block offset)'})
        data = (BytesBlock(length=lambda ctx: ctx.data('len')),
                {'usage': 'ui'})


class UnkPart4(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {**super().schema,
                'block_description': 'Unknown part with 4-chars identifier'}

    class Fields(DeclarativeCompoundBlock.Fields):
        identifier = (
            UTF8Block(length=4, value_validator=Or(['esaB', 'PdnB', 'htMR', 'odnW', 'nAmC', 'cseD', 'DmiS', 'TmiS',
                                                    ' siV', '', 'minA', 'tqnA'])),
            {'description': 'Identifier'})
        unk0 = (IntegerBlock(length=1),
                {'is_unknown': True})
        len = (IntegerBlock(length=3),
               {'description': 'Data length in bytes'})
        unk1 = (IntegerBlock(length=4),
                {'is_unknown': True})
        offset = (IntegerBlock(length=4),
                  {'usage': 'io,doc',
                   'description': 'Data offset (Relative from current block offset)'})
        data = (BytesBlock(length=lambda ctx: ctx.data('len')),
                {'usage': 'ui'})


class MaterialPartData(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {**super().schema,
                'block_description': 'A material, data structure is mostly unknown'}

    class Fields(DeclarativeCompoundBlock.Fields):
        unk0 = (BytesBlock(length=16), {'is_unknown': True})
        desc = (UTF8Block(length=16), {'description': 'Description'})
        unk1 = (BytesBlock(length=8), {'is_unknown': True})
        tex_page_index = (IntegerBlock(length=4),
                          {'description': 'Texture page index'})
        unk2 = (BytesBlock(length=0x10C), {'is_unknown': True})


class MaterialPart(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {**super().schema,
                'block_description': 'A part referencing to [MaterialPartData](#materialpartdata) block'}

    class Fields(DeclarativeCompoundBlock.Fields):
        idx = (IntegerBlock(length=2),
               {'description': 'A part index of the same identifier'})
        identifier = (UTF8Block(length=2, value_validator=Eq("tm")),
                      {'description': 'Identifier'})
        unk0 = (IntegerBlock(length=1),
                {'is_unknown': True})
        len = (IntegerBlock(length=3),
               {'description': 'Data length in bytes'})
        unk1 = (IntegerBlock(length=4),
                {'is_unknown': True})
        offset = (IntegerBlock(length=4),
                  {'usage': 'io,doc',
                   'description': 'Data offset (Relative from current block offset)'})
        data = (MaterialPartData(), {'usage': 'ui'})


class FSHPart(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {**super().schema,
                'block_description': 'A part referencing to an array of [ShpiBlock](#shpiblock) blocks'}

    class Fields(DeclarativeCompoundBlock.Fields):
        idx = (IntegerBlock(length=2),
               {'description': 'A part index of the same identifier'})
        identifier = (UTF8Block(length=2, value_validator=Eq("fs")),
                      {'description': 'Identifier'})
        unk0 = (IntegerBlock(length=1),
                {'is_unknown': True})
        len = (IntegerBlock(length=3, programmatic_value=lambda ctx: sum(ShpiBlock().estimate_packed_size(shpi, None)
                                                                         for shpi in ctx.data('data'))),
               {'usage': 'io,doc',
                'description': 'Data length in bytes'})
        num_data = (IntegerBlock(length=4, programmatic_value=lambda ctx: len(ctx.data('data'))),
                    {'description': 'Number of SHPI blocks'})
        offset = (IntegerBlock(length=4),
                  {'usage': 'io,doc',
                   'description': 'Data offset (Relative from current block offset)'})
        data = (ArrayBlock(child=ShpiBlock(), length=lambda ctx: ctx.data('num_data')),
                {'usage': 'ui'})


class TextPart2(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {**super().schema,
                'block_description': 'A part referencing to text with index and 2-chars identifier'}

    class Fields(DeclarativeCompoundBlock.Fields):
        idx = (IntegerBlock(length=2),
               {'description': 'A part index of the same identifier (in the same article)'})
        identifier = (UTF8Block(length=2, value_validator=Eq('ns')),
                      {'description': 'Identifier'})
        unk0 = (IntegerBlock(length=1),
                {'is_unknown': True})
        len = (IntegerBlock(length=3, programmatic_value=lambda ctx: len(ctx.data('data')) + 1),
               {'description': 'Data length in bytes, equals to `text length + 1` (0x00 terminating byte)'})
        unk1 = (IntegerBlock(length=4),
                {'is_unknown': True})
        offset = (IntegerBlock(length=4),
                  {'usage': 'io,doc',
                   'description': 'Data offset (Relative from current block offset)'})
        data = (NullTerminatedUTF8Block(length=None),
                {'usage': 'ui'})


class TextPart4(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {**super().schema,
                'block_description': 'A part referencing to text with 4-chars identifier'}

    class Fields(DeclarativeCompoundBlock.Fields):
        identifier = (UTF8Block(length=4, value_validator=Or(['emaN', 'cseD'])),
                      {'description': 'Identifier'})
        unk0 = (IntegerBlock(length=1),
                {'is_unknown': True})
        len = (IntegerBlock(length=3, programmatic_value=lambda ctx: len(ctx.data('data')) + 1),
               {'description': 'Data length in bytes, equals to `text length + 1` (0x00 terminating byte)'})
        unk1 = (IntegerBlock(length=4),
                {'is_unknown': True})
        offset = (IntegerBlock(length=4),
                  {'usage': 'io,doc',
                   'description': 'Data offset (Relative from current block offset)'})
        data = (NullTerminatedUTF8Block(length=None),
                {'usage': 'ui'})


class CullingPartData(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {**super().schema,
                'block_description': 'Polygon culling rule?'}

    class Fields(DeclarativeCompoundBlock.Fields):
        normal = Point3D(child=DecimalBlock(length=4), is_normalized=True)
        threshold = DecimalBlock(length=4)


class CullingPart(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {**super().schema,
                'block_description': 'A part referencing to an array of [CullingPartData](#cullingpartdata) blocks'}

    class Fields(DeclarativeCompoundBlock.Fields):
        part_info = (CrpPartInfo1(),
                     {'description': 'Part matching info. Part should be used with others that have same values'})
        identifier = (UTF8Block(length=2, value_validator=Eq("n$")),
                      {'description': 'Identifier'})
        unk0 = (IntegerBlock(length=1),
                {'is_unknown': True})
        len = (IntegerBlock(length=3, programmatic_value=lambda ctx: len(ctx.data('data')) * 16),
               {'description': 'Data length in bytes'})
        num_data = (IntegerBlock(length=4, programmatic_value=lambda ctx: len(ctx.data('data'))),
                    {'description': 'Number of culling part data blocks'})
        offset = (IntegerBlock(length=4),
                  {'usage': 'io,doc',
                   'description': 'Data offset (Relative from current block offset)'})
        data = (ArrayBlock(length=lambda ctx: ctx.data('num_data'), child=CullingPartData()),
                {'usage': 'ui'})


class TransformationPart(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {**super().schema,
                'block_description': 'A part referencing to a transformation matrix. If exists, matrix should be '
                                     'applied to the mesh. Matrix is a 4x4 matrix in row-major order, where each number '
                                     'is stored as 4-bytes float number (little-endian).'}

    class Fields(DeclarativeCompoundBlock.Fields):
        part_info = (CrpPartInfo1(),
                     {'description': 'Part matching info. Part should be used with others that have same values'})
        identifier = (UTF8Block(length=2, value_validator=Eq('rt')),
                      {'description': 'Identifier'})
        unk0 = (IntegerBlock(length=1),
                {'is_unknown': True})
        len = (IntegerBlock(length=3, value_validator=Eq(0x40)),
               {'description': 'Data length in bytes'})
        unk_1 = (IntegerBlock(length=4),
                 {'is_unknown': True,
                  'description': 'Always 1? Number of Transformation Matrices?'})
        offset = (IntegerBlock(length=4),
                  {'usage': 'io,doc',
                   'description': 'Data offset (Relative from current block offset)'})
        data = (ArrayBlock(length=16, child=DecimalBlock(length=4)),
                {'usage': 'ui'})


class VertexData(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {**super().schema,
                'block_description': 'Represents single vertex'}

    class Fields(DeclarativeCompoundBlock.Fields):
        position = (Point3D(child=DecimalBlock(length=4)),
                    {'description': 'Position'})
        unk = (DecimalBlock(length=4), {'is_unknown': True})


class VertexPart(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {**super().schema,
                'block_description': 'A part referencing to an array of [VertexData](#vertexdata) blocks, representing'
                                     ' mesh vertices'}

    class Fields(DeclarativeCompoundBlock.Fields):
        part_info = (CrpPartInfo1(),
                     {'description': 'Part matching info. Part should be used with others that have same values'})
        identifier = (UTF8Block(length=2, value_validator=Eq("tv")),
                      {'description': 'Identifier'})
        unk0 = (IntegerBlock(length=1),
                {'is_unknown': True})
        len = (IntegerBlock(length=3, programmatic_value=lambda ctx: len(ctx.data('data')) * 16),
               {'usage': 'io,doc',
                'description': 'Data length in bytes'})
        num_vertices = (IntegerBlock(length=4, programmatic_value=lambda ctx: len(ctx.data('data'))),
                        {'description': 'Number of vertices'})
        offset = (IntegerBlock(length=4),
                  {'usage': 'io,doc',
                   'description': 'Data offset (Relative from current block offset)'})
        data = (ArrayBlock(length=lambda ctx: ctx.data('num_vertices'), child=VertexData()),
                {'usage': 'ui'})


class NormalPartData(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        normal = (Point3D(child=DecimalBlock(length=4)),
                  {'description': 'Normal vector'})
        unk = (DecimalBlock(length=4), {'is_unknown': True})


class NormalPart(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {**super().schema,
                'block_description': 'A part referencing to an array of [NormalPartData](#normalpartdata) blocks, describing mesh normals'}

    class Fields(DeclarativeCompoundBlock.Fields):
        part_info = (CrpPartInfo1(),
                     {'description': 'Part matching info. Part should be used with others that have same values'})
        identifier = (UTF8Block(length=2, value_validator=Eq('mn')),
                      {'description': 'Identifier'})
        unk0 = (IntegerBlock(length=1),
                {'is_unknown': True})
        len = (IntegerBlock(length=3, programmatic_value=lambda ctx: ctx.data('num_data') * 16),
               {'description': 'Data length in bytes'})
        num_data = (IntegerBlock(length=4, programmatic_value=lambda ctx: len(ctx.data('data'))),
                    {'description': 'Number of normals'})
        offset = (IntegerBlock(length=4),
                  {'usage': 'io,doc',
                   'description': 'Data offset (Relative from current block offset)'})
        data = (ArrayBlock(length=lambda ctx: ctx.data('num_data'), child=NormalPartData()),
                {'usage': 'ui'})


class UVData(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        u = DecimalBlock(length=4)
        v = DecimalBlock(length=4)


class UVPart(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {**super().schema,
                'block_description': 'A part referencing to an array of [UVData](#uvdata) blocks, representing texture coordinates'}

    class Fields(DeclarativeCompoundBlock.Fields):
        part_info = (CrpPartInfo1(),
                     {'description': 'Part matching info. Part should be used with others that have same values'})
        identifier = (UTF8Block(length=2, value_validator=Eq('vu')),
                      {'description': 'Identifier'})
        unk0 = (IntegerBlock(length=1),
                {'is_unknown': True})
        len = (IntegerBlock(length=3, programmatic_value=lambda ctx: ctx.data('num_data') * 8),
               {'description': 'Data length in bytes'})
        num_data = (IntegerBlock(length=4, programmatic_value=lambda ctx: len(ctx.data('data'))),
                    {'description': 'Amount of UVData blocks, equals to len / 8'})
        offset = (IntegerBlock(length=4),
                  {'usage': 'io,doc',
                   'description': 'Data offset (Relative from current block offset)'})
        data = (ArrayBlock(length=lambda ctx: ctx.data('num_data'), child=UVData()),
                {'usage': 'ui'})


class TriangleInfoRowBase(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        unk0 = (IntegerBlock(length=4), {'is_unknown': True})
        offset = (IntegerBlock(length=4), {'description': 'Offset in data'})
        length_used = (IntegerBlock(length=2), {'description': 'Length used'})


class CullingInfoRow(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        unk0 = (IntegerBlock(length=4), {'is_unknown': True})
        offset = (IntegerBlock(length=4), {'description': 'Offset in culling data'})
        length_used = (IntegerBlock(length=2), {'description': 'Length of culling data used'})
        identifier = (UTF8Block(length=2), {'description': 'Identifier ("n$")'})
        level_index = (IntegerBlock(length=2), {'description': 'Level index'})
        unk1 = (IntegerBlock(length=2), {'is_unknown': True})


class VertexInfoRow(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        unk0 = (IntegerBlock(length=4), {'is_unknown': True})
        offset = (IntegerBlock(length=4), {'description': 'Offset in vertex data'})
        length_used = (IntegerBlock(length=2), {'description': 'Length of vertex data used'})
        unk1 = (BytesBlock(length=2), {'is_unknown': True})
        level_index = (IntegerBlock(length=2), {'description': 'Level index'})
        unk2 = (IntegerBlock(length=2), {'is_unknown': True})


class NormalInfoRow(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        unk0 = (IntegerBlock(length=4), {'is_unknown': True})
        offset = (IntegerBlock(length=4), {'description': 'Offset in normal data'})
        length_used = (IntegerBlock(length=2), {'description': 'Length of normal data used'})
        unk1 = (BytesBlock(length=2), {'is_unknown': True})
        level_index = (IntegerBlock(length=2), {'description': 'Level index'})
        unk2 = (IntegerBlock(length=2), {'is_unknown': True})


class UVInfoRow(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        unk0 = (IntegerBlock(length=4), {'is_unknown': True})
        offset = (IntegerBlock(length=4), {'description': 'Offset in uv data'})
        length_used = (IntegerBlock(length=2), {'description': 'Length of uv data used'})
        unk1 = (BytesBlock(length=2), {'is_unknown': True})
        level_index = (IntegerBlock(length=2), {'description': 'Level index'})
        unk2 = (IntegerBlock(length=2), {'is_unknown': True})


def determine_triangle_info_row_type(ctx, name):
    if ctx.data('../num_info_rows') == 4:
        # CullingRow, NormalRow, UVRow, VertexRow
        return int(name)
    elif ctx.data('../num_info_rows') == 3:
        # NormalRow, UVRow, VertexRow
        return int(name) + 1
    else:
        raise BlockDefinitionException(f'Unexpected number of info rows: {ctx.data("../num_info_rows")}')


class IndexRow(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        idx = (IntegerBlock(length=2), {'description': 'Row index'})
        identifier = (UTF8Block(length=2),
                      {'description': 'Identifier "vI"|"Iv" – vertex index, "uI"|"Iu" - uv index'})
        offset = (IntegerBlock(length=4), {'description': 'Offset of indices'})


class TrianglePartData(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {**super().schema,
                'block_description': 'A description of mesh geometry (faces)'}

    class Fields(DeclarativeCompoundBlock.Fields):
        flags = (IntegerBlock(length=4), {'is_unknown': True, 'description': 'Info flags'})
        material_index = (IntegerBlock(length=2), {'description': 'Material index'})
        unk0 = (IntegerBlock(length=2), {'is_unknown': True})
        unk_floats = (ArrayBlock(length=4, child=DecimalBlock(length=4)), {'is_unknown': True})
        unk_zeros = (BytesBlock(length=16), {'is_unknown': True})
        num_info_rows = (IntegerBlock(length=4), {'programmatic_value': lambda ctx: len(ctx.data('info_rows')),
                                                  'description': 'Number of info rows'})
        num_index_rows = (IntegerBlock(length=4), {'programmatic_value': lambda ctx: len(ctx.data('index_rows')),
                                                   'description': 'Number of index rows'})
        info_rows = ArrayBlock(length=lambda ctx: ctx.data('num_info_rows'),
                               child=DelegateBlock(
                                   possible_blocks=[CullingInfoRow(), NormalInfoRow(), UVInfoRow(), VertexInfoRow()],
                                   choice_index=lambda ctx, name: determine_triangle_info_row_type(ctx, name)))
        index_rows = ArrayBlock(length=lambda ctx: ctx.data('num_index_rows'), child=IndexRow())
        index_table = (ArrayBlock(length=lambda ctx: ctx.data('../num_data'), child=IntegerBlock(length=1)),
                       {'description': 'Vertex index table'})
        uv_index_table = (ArrayBlock(length=lambda ctx: ctx.data('../num_data'), child=IntegerBlock(length=1)),
                          {'description': 'UV index table'})


class TrianglePart(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {**super().schema,
                'block_description': 'A part referencing to [TrianglePartData](#TrianglePartData) block, describes mesh faces'}

    class Fields(DeclarativeCompoundBlock.Fields):
        part_info = (CrpPartInfo2(),
                     {'description': 'Part matching info. Part should be used with others that have same values'})
        identifier = (UTF8Block(length=2, value_validator=Eq('rp')),
                      {'description': 'Identifier'})
        unk0 = (IntegerBlock(length=1),
                {'is_unknown': True})
        # TODO setup programmatic value for length fields. Here it should be (48 + data.num_info_rows*16 + data.num_index_rows*8 + num_data*2)
        len = (IntegerBlock(length=3),
               {'description': 'Data length in bytes'})
        num_data = (IntegerBlock(length=4),
                    {'description': 'Number of indices'})
        offset = (IntegerBlock(length=4),
                  {'usage': 'io,doc',
                   'description': 'Data offset (Relative from current block offset)'})
        data = (TrianglePartData(), {'usage': 'ui'})


class EffectPartData(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        unk0 = (IntegerBlock(length=4), {'is_unknown': True})
        unk1 = (IntegerBlock(length=4), {'is_unknown': True})
        position = (Point3D(child=DecimalBlock(length=4)), {'description': 'Position'})
        unk_scale = (DecimalBlock(length=4), {'is_unknown': True})
        width = (Point3D(child=DecimalBlock(length=4)), {'description': 'Width relative to position'})
        unk2 = (DecimalBlock(length=4), {'is_unknown': True})
        height = (Point3D(child=DecimalBlock(length=4)), {'description': 'Height relative to position'})
        unk3 = (DecimalBlock(length=4), {'is_unknown': True})
        depth = (Point3D(child=DecimalBlock(length=4)), {'description': 'Depth relative to position'})
        unk4 = (DecimalBlock(length=4), {'is_unknown': True})
        glow_color = (IntegerBlock(length=4), {'description': 'Color of glow (BGRA)'})
        source_color = (IntegerBlock(length=4), {'description': 'Color of source (BGRA)'})
        mirror = (IntegerBlock(length=4), {'description': 'Mirror'})
        info = (IntegerBlock(length=4), {'is_unknown': True, 'description': 'Information'})


class EffectPart(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {**super().schema,
                'block_description': 'A part referencing to an array of [EffectPartData](#effectpartdata) blocks'}

    class Fields(DeclarativeCompoundBlock.Fields):
        part_info = (CrpPartInfo1(),
                     {'description': 'Part matching info. Part should be used with others that have same values'})
        identifier = (UTF8Block(length=2, value_validator=Eq('fe')),
                      {'description': 'Identifier'})
        unk0 = (IntegerBlock(length=1),
                {'is_unknown': True})
        len = (IntegerBlock(length=3, programmatic_value=lambda ctx: 0x58),
               {'description': 'Data length in bytes'})
        unk1 = (IntegerBlock(length=4),
                {'is_unknown': True})
        offset = (IntegerBlock(length=4),
                  {'usage': 'io,doc',
                   'description': 'Data offset (Relative from current block offset)'})
        data = (EffectPartData(), {'usage': 'ui'})


class PartBlock(DelegateBlock):
    def __init__(self, **kwargs):
        super().__init__(possible_blocks=[TextPart4(),
                                          CullingPart(),
                                          TextPart2(),
                                          EffectPart(),
                                          NormalPart(),
                                          TrianglePart(),
                                          TransformationPart(),
                                          UVPart(),
                                          VertexPart(),
                                          UnkPart4(),
                                          UnkPart2()],
                         choice_index=lambda ctx, **_: _determine_part_type(ctx),
                         **kwargs)


class ArticlePart(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {**super().schema,
                'block_description': 'Article is a single logical part of a car or track. Contains meshes of the same '
                                     'entity for various levels of details, damage status, animation indexes etc.'}

    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (UTF8Block(value_validator=Eq('itrA'), length=4),
                       {'description': 'Resource ID'})
        header_info = (IntegerBlock(length=4, value_validator=Eq(0x1A)),
                       {'is_unknown': True})
        num_parts = (IntegerBlock(length=4),
                     {'description': 'An amount of parts, linked to this article'})
        local_offset = (IntegerBlock(length=4),
                        {'description': 'A local offset from the beginning of this article to the first linked part, '
                                        'divided by 16. So the first part index in parts array for this article is: '
                                        'local_offset + this article index - len(articles) - len(common_parts)'})
        parts = (ArrayBlock(child=PartBlock(), length=(0, '?')), {'usage': 'ui'})


def determine_common_part_type(ctx):
    (TEXT4, MAT, FSH, TEXT2, UNK4, UNK2) = range(6)
    try:
        first_part = ctx.buffer.read(2).decode('utf-8')
    except UnicodeDecodeError:
        first_part = None
    try:
        second_part = ctx.buffer.read(2).decode('utf-8')
    except UnicodeDecodeError:
        second_part = None
    ctx.buffer.seek(-4, SEEK_CUR)
    if second_part == 'tm':
        return MAT
    elif second_part == 'fs':
        return FSH
    elif second_part == 'ns':
        return TEXT2
    elif first_part is not None:
        id = first_part + second_part
        if id == 'cseD':
            return TEXT4
    return UNK4


def _determine_part_type(ctx):
    (TEXT4, CULL, TEXT2, FX, NRML, TRNGL, TRANSF, UV, VRTX, UNK4, UNK2) = range(11)
    try:
        first_part = ctx.buffer.read(2).decode('utf-8')
    except UnicodeDecodeError:
        first_part = None
    try:
        second_part = ctx.buffer.read(2).decode('utf-8')
    except UnicodeDecodeError:
        second_part = None
    ctx.buffer.seek(-4, SEEK_CUR)

    if second_part == 'n$':
        return CULL
    elif second_part == 'rt':
        return TRANSF
    elif second_part == 'tv':
        return VRTX
    elif second_part == 'mn':
        return NRML
    elif second_part == 'vu':
        return UV
    elif second_part == 'rp':
        return TRNGL
    elif second_part == 'fe':
        return FX
    elif second_part == 'ns':
        return TEXT2
    elif second_part == 'zd' or second_part == 'fd':
        return UNK2
    elif first_part is not None:
        id = first_part + second_part
        if id == 'esaB' or id == '\x00\x00\x00\x00' or id == 'minA' or id == 'tqnA':
            return UNK4
        elif id == 'emaN':
            return TEXT4
    raise BlockDefinitionException(f'Unknown part type: {first_part}{second_part}')


def determine_num_parts(ctx):
    last_used_part_indices = [a['local_offset'] + a['num_parts'] + i for (i, a) in enumerate(ctx.data('articles'))]
    return max(last_used_part_indices) - len(ctx.data('articles')) - len(ctx.data('common_parts')) + 1


class CrpGeometry(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {**super().schema,
                'block_description': 'A set of 3D meshes, used for cars and tracks. Currently I parsed all geometries '
                                     'and (possibly) UV-s, materials are not parsed yet. Contains many part blocks, '
                                     '16-bytes each, splitted into 3 sections: articles, common_parts, parts, followed '
                                     'by raw data. Each part, except articles, have an offset and length of it\'s data,'
                                     ' located in "raw_data" byte array'}

    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (UTF8Block(value_validator=Or([' raC', 'karT']), length=4),
                       {'description': 'Resource ID. " raC" ("Car ") for cars, "karT" for tracks'})
        header_info = (IntegerBlock(length=4, programmatic_value=lambda ctx: 0x1A | (len(ctx.data('articles')) << 5)),
                       {'description': 'Header info: 27 higher bits: number of articles; 5 lower bits: unknown, always '
                                       'seems to be 0x1A'})
        num_common_parts = (IntegerBlock(length=4, programmatic_value=lambda ctx: len(ctx.data('common_parts'))),
                            {'description': 'Number of common parts'})
        articles_offset = (IntegerBlock(length=4, value_validator=Eq(1)),
                           {'description': 'Offset to articles block / 16'})
        articles = (ArrayBlock(child=ArticlePart(), length=(lambda ctx: ctx.data('header_info') >> 5)),
                    {'description': 'Array of articles'})
        common_parts = (ArrayBlock(child=DelegateBlock(possible_blocks=[TextPart4(),
                                                                        MaterialPart(),
                                                                        FSHPart(),
                                                                        TextPart2(),
                                                                        UnkPart4(),
                                                                        UnkPart2(),
                                                                        ],
                                                       choice_index=lambda ctx, **_: determine_common_part_type(ctx)),
                                   length=lambda ctx: ctx.data('num_common_parts')),
                        {
                            'description': 'Array of common parts. They are ordered by type (identifier). The order is:<br/>' +
                                           '- "PdnB" - ?, cars only<br/>'
                                           '- "nAmC" - camera animations? tracks only<br/>'
                                           '- [TextPart4](#textpart4) "cseD" - seems to be a path to original development source file, tracks only<br/>'
                                           '- "htMR" - ?<br/>'
                                           '- "odnW" - ?, cars only<br/>'
                                           '- "DmiS" - ?, tracks only<br/>'
                                           '- "TmiS" - ?, tracks only<br/>'
                                           '- " siV" - ?, tracks only<br/>'
                                           '- [MaterialPart](#materialpart)<br/>'
                                           '- [FSHPart](#fshpart)<br/>'
                                           '- [TextPart2](#textpart2) "ns" - a path to fsh file with textures, tracks only'})
        parts = (ArrayBlock(child=PartBlock(),
                            length=(lambda ctx: determine_num_parts(ctx),
                                    '1 + last referenced part index in articles data')),
                 {'usage': 'io,doc',
                  'description': 'Array of parts, ordered by article, for each article it is also ordered by type (identifier):<br/>'
                                 '- "minA" - animations? tracks only<br/>'
                                 '- "tqnA" - ?, tracks only<br/>'
                                 '- [CullingPart](#cullingpart) - ?, cars only<br/>'
                                 '- "esaB" - ?<br/>'
                                 '- [TextPart4](#textpart4) "emaN" - name of the mesh<br/>'
                                 '- "fd" - ?, tracks only<br/>'
                                 '- [EffectPart](#effectpart) - ?<br/>'
                                 '- "zd" - ?, cars only<br/>'
                                 '- [NormalPart](#normalpart) - ?, cars only<br/>'
                                 '- [TrianglePart](#trianglepart) - mesh indexes (faces)<br/>'
                                 '- [TransformationPart](#transformationpart) - position/rotation of the mesh<br/>'
                                 '- [UVPart](#uvpart) - vertex UV-s<br/>'
                                 '- [VertexPart](#vertexpart) - vertices'})
        raw_data = (BytesBlock(length=lambda ctx: ctx.read_bytes_remaining),
                    {'usage': 'doc',
                     'description': 'Raw data region, where part data is stored. Part data offset and lengthes are stored in the PartBlock.'})

    def read(self, ctx: ReadContext, name: str = '', read_bytes_amount=None):
        data = super().read(ctx, name, read_bytes_amount)
        misc_part_block = self.field_blocks_map.get('common_parts').child
        self_ctx = ctx.get_or_create_child(name, self, read_bytes_amount)

        raw_data_offset = ctx.buffer.tell()
        raw_data_len = ctx.read_bytes_remaining

        for (i, misc_part) in enumerate(data['common_parts']):
            misc_block = misc_part_block.possible_blocks[misc_part['choice_index']]
            data_block = misc_block.field_blocks_map.get('data')
            if not data_block:
                continue
            ctx.buffer.seek(raw_data_offset + misc_part['data']['offset']
                            - 16 * (len(data['parts']) + len(data['common_parts']) - i))
            misc_part['data']['data'] = data_block.read(self_ctx.child(f"common_parts/{i}"),
                                                        'data',
                                                        read_bytes_amount=misc_part['data']['len'])
        part_block = self.field_blocks_map.get('parts').child
        for (i, part) in enumerate(data['parts']):
            block = part_block.possible_blocks[part['choice_index']]
            data_block = block.field_blocks_map.get('data')
            if not data_block:
                continue
            ctx.buffer.seek(raw_data_offset + part['data']['offset']
                            - 16 * (len(data['parts']) - i))
            part['data']['data'] = data_block.read(self_ctx.child(f"parts/{i}"),
                                                   'data',
                                                   read_bytes_amount=part['data']['len'])
        for (i, article) in enumerate(data['articles']):
            offs = article['local_offset'] - len(data['articles']) - len(data['common_parts']) + i
            article['parts'] = data['parts'][offs:offs + article['num_parts']]
        ctx.buffer.seek(raw_data_offset + raw_data_len)
        return data

    def serializer_class(self):
        from serializers import CrpGeometrySerializer
        return CrpGeometrySerializer
