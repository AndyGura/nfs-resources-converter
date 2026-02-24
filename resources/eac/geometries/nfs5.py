from os import SEEK_CUR

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
            'block_description': 'Part info type 1: [dddd_aaaa_aaaa_pppp]'
                                 '<br/>d - damage level'
                                 '<br/>a - animation index'
                                 '<br/>p - part index',
        }

    def __init__(self, **kwargs):
        super().__init__(length=2, is_signed=False, **kwargs)

    def read(self, ctx: ReadContext, name: str = '', read_bytes_amount=None):
        data = super().read(ctx, name, read_bytes_amount)
        return {
            'damage': data >> 12,
            'animation_index': (data >> 4) & 0xff,
            'part_index': data & 0xf,
        }

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        value = data['damage'] << 12
        value = value | (data['animation_index'] << 4)
        value = value | data['part_index']
        return super().write(value, ctx, name)


class CrpPartInfo2(IntegerBlock):
    @property
    def schema(self):
        return {
            **super().schema,
            'block_description': 'Part info type 2: [pppp_uuuu_uuuu_dddd]'
                                 '<br/>p - part index'
                                 '<br/>u - unknown'
                                 '<br/>d - damage level',
        }

    def __init__(self, **kwargs):
        super().__init__(length=2, is_signed=False, **kwargs)

    def read(self, ctx: ReadContext, name: str = '', read_bytes_amount=None):
        data = super().read(ctx, name, read_bytes_amount)
        return {
            'part_index': data >> 12,
            'unk': (data >> 4) & 0xff,
            'detail_level': data & 0xf,
        }

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        value = data['part_index'] << 12
        value = value | (data['unk'] << 4)
        value = value | data['detail_level']
        return super().write(value, ctx, name)


class MiscPart(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        identifier = (UTF8Block(length=4),
                      {'description': 'Identifier'})
        unk0 = (IntegerBlock(length=1),
                {'is_unknown': True})
        len = (IntegerBlock(length=3),
               {'description': 'Length'})
        unk1 = (IntegerBlock(length=4),
                {'is_unknown': True})
        offset = (IntegerBlock(length=4),
                  {'usage': 'skip_ui',
                   'description': 'Offset (Relative from current MiscPart offset)'})
        data = (BytesBlock(length=lambda ctx: ctx.data('len')),
                {'usage': 'ui_only'})


class MaterialPartData(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        unk0 = (BytesBlock(length=16), {'is_unknown': True})
        desc = (UTF8Block(length=16), {'description': 'Description'})
        unk1 = (BytesBlock(length=8), {'is_unknown': True})
        tex_page_index = (IntegerBlock(length=4),
                          {'description': 'Texture page index'})
        unk2 = (BytesBlock(length=0x10C), {'is_unknown': True})


class MaterialPart(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        index = (IntegerBlock(length=2),
                 {'description': 'Index'})
        identifier = (UTF8Block(length=2),
                      {'description': 'Identifier ("tm"/"mt")'})
        unk0 = (IntegerBlock(length=1),
                {'is_unknown': True})
        len = (IntegerBlock(length=3),
               {'description': 'Length'})
        unk1 = (IntegerBlock(length=4),
                {'is_unknown': True})
        offset = (IntegerBlock(length=4),
                  {'usage': 'skip_ui',
                   'description': 'Offset (Relative from current MaterialPart offset)'})
        data = (MaterialPartData(), {'usage': 'ui_only'})


class FSHPart(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        index = (IntegerBlock(length=2),
                 {'description': 'Index'})
        identifier = (UTF8Block(length=2),
                      {'description': 'Identifier ("fs"/"sf")'})
        unk0 = (IntegerBlock(length=1),
                {'is_unknown': True})
        len = (IntegerBlock(length=3, programmatic_value=lambda ctx: sum(ShpiBlock().estimate_packed_size(shpi, None)
                                                                         for shpi in ctx.data('data'))),
               {'usage': 'skip_ui',
                'description': 'Length'})
        num_fsh = (IntegerBlock(length=4, programmatic_value=lambda ctx: len(ctx.data('data'))),
                   {'description': 'Number of FSH files'})
        offset = (IntegerBlock(length=4),
                  {'usage': 'skip_ui',
                   'description': 'Offset (Relative from current FSHPart offset)'})
        data = (ArrayBlock(child=ShpiBlock(), length=lambda ctx: ctx.data('num_fsh')),
                {'usage': 'ui_only'})


class BasePart(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        identifier = (UTF8Block(length=4),
                      {'description': 'Identifier'})
        unk0 = (IntegerBlock(length=1),
                {'is_unknown': True})
        len = (IntegerBlock(length=3),
               {'description': 'Length'})
        unk1 = (IntegerBlock(length=4),
                {'is_unknown': True})
        offset = (IntegerBlock(length=4),
                  {'usage': 'skip_ui',
                   'description': 'Offset (Relative from current MiscPart offset)'})
        data = (BytesBlock(length=lambda ctx: ctx.data('len')),
                {'usage': 'ui_only'})


class NamePart(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        identifier = (UTF8Block(length=4),
                      {'description': 'Identifier'})
        unk0 = (IntegerBlock(length=1),
                {'is_unknown': True})
        len = (IntegerBlock(length=3, programmatic_value=lambda ctx: len(ctx.data('data')) + 1),
               {'description': 'Length'})
        unk1 = (IntegerBlock(length=4),
                {'is_unknown': True})
        offset = (IntegerBlock(length=4),
                  {'usage': 'skip_ui',
                   'description': 'Offset (Relative from current MiscPart offset)'})
        data = (NullTerminatedUTF8Block(length=None),
                {'usage': 'ui_only'})


class CullingPartData(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        normal = Point3D(child=DecimalBlock(length=4), is_normalized=True)
        threshold = DecimalBlock(length=4)


class CullingPart(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        part_info = CrpPartInfo1()
        identifier = (UTF8Block(length=2),
                      {'description': 'Identifier ("n$"/"$n")'})
        unk0 = (IntegerBlock(length=1),
                {'is_unknown': True})
        len = (IntegerBlock(length=3, programmatic_value=lambda ctx: len(ctx.data('data')) * 16),
               {'description': 'Length'})
        num_data = IntegerBlock(length=4, programmatic_value=lambda ctx: len(ctx.data('data')))
        offset = (IntegerBlock(length=4),
                  {'usage': 'skip_ui',
                   'description': 'Offset (Relative from current MiscPart offset)'})
        data = (ArrayBlock(length=lambda ctx: ctx.data('num_data'), child=CullingPartData()),
                {'usage': 'ui_only'})


class TransformationPart(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        part_info = CrpPartInfo1()
        identifier = (UTF8Block(length=2),
                      {'description': 'Identifier ("rt"/"tr")'})
        unk0 = (IntegerBlock(length=1),
                {'is_unknown': True})
        len = (IntegerBlock(length=3, programmatic_value=lambda ctx: ctx.data('num_matrices') * 0x40),
               {'description': 'Length'})
        num_matrices = (IntegerBlock(length=4, programmatic_value=lambda ctx: 1),
                        {'description': 'Number of Transformation Matrices (always 1)'})
        offset = (IntegerBlock(length=4),
                  {'usage': 'skip_ui',
                   'description': 'Offset (Relative from current MiscPart offset)'})
        data = (ArrayBlock(length=lambda ctx: ctx.data('num_matrices'),
                           child=ArrayBlock(length=16, child=DecimalBlock(length=4))),
                {'usage': 'ui_only'})


class VertexData(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        position = (Point3D(child=DecimalBlock(length=4)),
                    {'description': 'Position'})
        unk = (DecimalBlock(length=4), {'is_unknown': True})


class VertexPart(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        part_info = CrpPartInfo1()
        identifier = (UTF8Block(length=2),
                      {'description': 'Identifier ("tv"/"vt")'})
        unk0 = (IntegerBlock(length=1),
                {'is_unknown': True})
        len = (IntegerBlock(length=3, programmatic_value=lambda ctx: len(ctx.data('data')) * 16),
               {'usage': 'skip_ui',
                'description': 'Length'})
        num_vertices = (IntegerBlock(length=4, programmatic_value=lambda ctx: len(ctx.data('data'))),
                        {'description': 'Number of vertices'})
        offset = (IntegerBlock(length=4),
                  {'usage': 'skip_ui',
                   'description': 'Offset (Relative from current part offset)'})
        data = (ArrayBlock(length=lambda ctx: ctx.data('num_vertices'), child=VertexData()),
                {'usage': 'ui_only'})


class NormalData(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        normal = (Point3D(child=DecimalBlock(length=4)),
                  {'description': 'Normal'})
        unk = (DecimalBlock(length=4), {'is_unknown': True})


class NormalPart(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        part_info = CrpPartInfo1()
        identifier = (UTF8Block(length=2),
                      {'description': 'Identifier ("mn"/"nm")'})
        unk0 = (IntegerBlock(length=1),
                {'is_unknown': True})
        len = (IntegerBlock(length=3, programmatic_value=lambda ctx: ctx.data('num_normals') * 16),
               {'description': 'Length'})
        num_normals = (IntegerBlock(length=4, programmatic_value=lambda ctx: len(ctx.data('data'))),
                       {'description': 'Number of normals'})
        offset = (IntegerBlock(length=4),
                  {'usage': 'skip_ui',
                   'description': 'Offset (Relative from current MiscPart offset)'})
        data = (ArrayBlock(length=lambda ctx: ctx.data('num_normals'), child=NormalData()),
                {'usage': 'ui_only'})


class UVData(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        u = DecimalBlock(length=4)
        v = DecimalBlock(length=4)


class UVPart(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        part_info = CrpPartInfo1()
        identifier = (UTF8Block(length=2),
                      {'description': 'Identifier ("vu"/"uv")'})
        unk0 = (IntegerBlock(length=1),
                {'is_unknown': True})
        len = (IntegerBlock(length=3, programmatic_value=lambda ctx: ctx.data('num_data') * 8),
               {'description': 'Length'})
        num_data = IntegerBlock(length=4, programmatic_value=lambda ctx: len(ctx.data('data')))
        offset = (IntegerBlock(length=4),
                  {'usage': 'skip_ui',
                   'description': 'Offset (Relative from current MiscPart offset)'})
        data = (ArrayBlock(length=lambda ctx: ctx.data('num_data'), child=UVData()),
                {'usage': 'ui_only'})


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
        index = (IntegerBlock(length=2), {'description': 'Row index'})
        identifier = (UTF8Block(length=2),
                      {'description': 'Identifier "vI"|"Iv" – vertex index, "uI"|"Iu" - uv index'})
        offset = (IntegerBlock(length=4), {'description': 'Offset of indices'})


class TriangleData(DeclarativeCompoundBlock):
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
        index_table = ArrayBlock(length=lambda ctx: ctx.data('../num_indices'), child=IntegerBlock(length=1))


class TrianglePart(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        part_info = CrpPartInfo2()
        identifier = (UTF8Block(length=2),
                      {'description': 'Identifier ("rp"/"pr")'})
        unk0 = (IntegerBlock(length=1),
                {'is_unknown': True})
        len = (IntegerBlock(length=3),
               {'description': 'Length'})
        num_indices = (IntegerBlock(length=4),
                       {'description': 'Number of Indices'})
        offset = (IntegerBlock(length=4),
                  {'usage': 'skip_ui',
                   'description': 'Offset (Relative from current MiscPart offset)'})
        data = (TriangleData(), {'usage': 'ui_only'})


class EffectData(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        unk0 = (IntegerBlock(length=4), {'is_unknown': True})
        unk1 = (IntegerBlock(length=4, value_validator=Eq(0x00000000)), {'is_unknown': True})
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
    class Fields(DeclarativeCompoundBlock.Fields):
        part_info = CrpPartInfo1()
        identifier = (UTF8Block(length=2),
                      {'description': 'Identifier ("fe"/"ef")'})
        unk0 = (IntegerBlock(length=1),
                {'is_unknown': True})
        len = (IntegerBlock(length=3, programmatic_value=lambda ctx: 0x58),
               {'description': 'Length'})
        unk1 = (IntegerBlock(length=4),
                {'is_unknown': True})
        offset = (IntegerBlock(length=4),
                  {'usage': 'skip_ui',
                   'description': 'Offset (Relative from current MiscPart offset)'})
        data = (EffectData(), {'usage': 'ui_only'})


class PartBlock(DelegateBlock):
    def __init__(self, **kwargs):
        super().__init__(possible_blocks=[MiscPart(),
                                          BasePart(),
                                          NamePart(),
                                          CullingPart(),
                                          TransformationPart(),
                                          VertexPart(),
                                          NormalPart(),
                                          UVPart(),
                                          TrianglePart(),
                                          EffectPart()],
                         choice_index=lambda ctx, **_: self._determine_part_type(ctx),
                         **kwargs)

    def _determine_part_type(self, ctx):
        (MISC, BASE, NAME, CULL, TRANSF, VRTX, NRML, UV, TRNGL, FX) = range(10)
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
        elif first_part is not None:
            id = first_part + second_part
            if id == 'esaB':
                return BASE
            elif id == 'emaN':
                return NAME
        return MISC


class Article(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (UTF8Block(value_validator=Eq('itrA'), length=4),
                       {'description': 'Resource ID'})
        header_info = (IntegerBlock(length=4, value_validator=Eq(0x1A)),
                       {'is_unknown': True})
        len_parttable = (IntegerBlock(length=4),
                         {'description': 'Length of Parttable pointed to (* 16)'})
        offset = (IntegerBlock(length=4),
                  {'description': 'Offset (Relative from current Article offset * 16)'})
        parts = (ArrayBlock(child=PartBlock(), length=(0, '?')), {'usage': 'ui_only'})


def determine_misc_part_type(ctx):
    (MISC, MAT, FSH) = range(3)
    ctx.buffer.seek(2, SEEK_CUR)
    try:
        second_part = ctx.buffer.read(2).decode('utf-8')
    except UnicodeDecodeError:
        second_part = None
    ctx.buffer.seek(-4, SEEK_CUR)

    if second_part == 'tm':
        return MAT
    elif second_part == 'fs':
        return FSH
    return MISC


def determine_num_parts(ctx):
    last_used_part_indices = [
        a['offset'] + a['len_parttable'] + i - len(ctx.data('articles')) - len(ctx.data('misc_parts'))
        for (i, a) in enumerate(ctx.data('articles'))]
    return max(last_used_part_indices) + 1


class CrpGeometry(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (UTF8Block(value_validator=Or([' raC', 'karT']), length=4),
                       {'description': 'Resource ID'})
        header_info = (IntegerBlock(length=4, programmatic_value=lambda ctx: 0x1A | (len(ctx.data('articles')) << 5)),
                       {'description': 'Header info: 5 bits: unknown (always seems to be 0x1A), '
                                       '27 bits: number of parts'})
        num_misc_parts = (IntegerBlock(length=4, programmatic_value=lambda ctx: len(ctx.data('misc_parts'))),
                          {'description': 'Number of misc data blocks'})
        articles_offset = (IntegerBlock(length=4, value_validator=Eq(1)),
                           {'description': 'Offset to articles block'})
        articles = (ArrayBlock(child=Article(), length=lambda ctx: ctx.data('header_info') >> 5),
                    {'description': 'Array of articles'})
        misc_parts = (ArrayBlock(child=DelegateBlock(possible_blocks=[MiscPart(),
                                                                      MaterialPart(),
                                                                      FSHPart()],
                                                     choice_index=lambda ctx, **_: determine_misc_part_type(ctx)),
                                 length=lambda ctx: ctx.data('num_misc_parts')),
                      {'description': 'Array of misc parts'})
        parts = (ArrayBlock(child=PartBlock(),
                            length=lambda ctx: determine_num_parts(ctx)),
                 {'usage': 'skip_ui',
                  'description': 'Array of parts'})
        raw_data = (BytesBlock(length=lambda ctx: ctx.read_bytes_remaining),
                    {'usage': 'skip_ui',
                     'description': 'Raw data'})

    def read(self, ctx: ReadContext, name: str = '', read_bytes_amount=None):
        data = super().read(ctx, name, read_bytes_amount)
        end_pos = ctx.buffer.tell()
        misc_part_block = self.field_blocks_map.get('misc_parts').child
        self_ctx = ctx.get_or_create_child(name, self, read_bytes_amount)
        for (i, misc_part) in enumerate(data['misc_parts']):
            misc_block = misc_part_block.possible_blocks[misc_part['choice_index']]
            data_block = misc_block.field_blocks_map.get('data')
            if not data_block:
                continue
            ctx.buffer.seek(end_pos - len(data['raw_data']) + misc_part['data']['offset']
                            - 16 * (len(data['parts']) + len(data['misc_parts']) - i))
            misc_part['data']['data'] = data_block.read(self_ctx.child(f"misc_parts/{i}"),
                                                        'data',
                                                        read_bytes_amount=misc_part['data']['len'])
        part_block = self.field_blocks_map.get('parts').child
        for (i, part) in enumerate(data['parts']):
            block = part_block.possible_blocks[part['choice_index']]
            data_block = block.field_blocks_map.get('data')
            if not data_block:
                continue
            ctx.buffer.seek(end_pos - len(data['raw_data']) + part['data']['offset']
                            - 16 * (len(data['parts']) - i))
            part['data']['data'] = data_block.read(self_ctx.child(f"parts/{i}"),
                                                   'data',
                                                   read_bytes_amount=part['data']['len'])
        for (i, article) in enumerate(data['articles']):
            offs = article['offset'] - len(data['articles']) - len(data['misc_parts']) + i
            article['parts'] = data['parts'][offs:offs + article['len_parttable']]
        ctx.buffer.seek(end_pos)
        return data

    def serializer_class(self):
        from serializers import CrpGeometrySerializer
        return CrpGeometrySerializer
