from math import floor
from typing import Dict

from library2.read_blocks import (DeclarativeCompoundBlock,
                                  UTF8Block,
                                  IntegerBlock,
                                  ArrayBlock,
                                  BytesBlock,
                                  DelegateBlock,
                                  BitFlagsBlock)
from resources.eac.fields.misc import Point3D_32_7, Point3D_32_4, Nfs1Utf8Block


class OripPolygon(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'A geometry polygon',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        polygon_type = (IntegerBlock(length=1),
                        {'description': "Huh, that's a srange field. From my tests, if it is xxx0_0011, the "
                                        "polygon is a triangle. If xxx0_0100 - it's a quad. Also there is only "
                                        "one polygon for entire TNFS with type == 2 in burnt sienna props. If "
                                        "ignore this polygon everything still looks great"})
        mapping = (BitFlagsBlock(flag_names=[(0, 'two_sided'),
                                             (1, 'flip_normal'),
                                             (4, 'use_uv')]),
                   {'description': 'Rendering properties of the polygon'})
        texture_index = (IntegerBlock(length=1),
                         {'description': "The index of item in ORIP's texture_names block"})
        unk = (IntegerBlock(length=1),
               {'is_unknown': True})
        offset_3d = (IntegerBlock(length=4),
                     {'description': "The index in polygon_vertex_map_block ORIP's table. This index "
                                     "represents first vertex of this polygon, so in order to determine all "
                                     "vertex we load next 2 or 3 (if quad) indexes from polygon_vertex_map. "
                                     "Look at polygon_vertex_map_block description for more info"})
        offset_2d = (IntegerBlock(length=4),
                     {'description': "The same as offset_3d, also points to polygon_vertex_map_block, but used "
                                     "for texture coordinates. Look at polygon_vertex_map_block description "
                                     "for more info"})


class OripVertexUV(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Texture coordinates for vertex, where each coordinate is: '
                                 + IntegerBlock(length=4).schema['block_description']
                                 + '. The unit is a pixels amount of assigned texture. So it should be changed when selecting '
                                   'texture with different size',
            'inline_description': True,
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        u = IntegerBlock(length=4, is_signed=True)
        v = IntegerBlock(length=4, is_signed=True)


class OripTextureName(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'A settings of the texture. From what is known, contains name of bitmap',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        type = Nfs1Utf8Block(length=8)
        file_name = (Nfs1Utf8Block(length=4),
                     {'description': 'Name of bitmap in SHPI block'})
        unknown = (BytesBlock(length=8),
                   {'is_unknown': True})


class RenderOrderBlock(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        identifier = (UTF8Block(length=8),
                      {'description': "identifier ('NON-SORT', 'inside', 'surface', 'outside')"})
        unk0 = (IntegerBlock(length=4),
                {'description': "0x8 for 'NON-SORT' or 0x1 for the others"})
        polygons_amount = (IntegerBlock(length=4),
                           {'description': "Polygons amount (3DO). For TNFSSE sometimes too big value"})
        polygon_sum = (IntegerBlock(length=4),
                       {'description': "0 for 'NON-SORT'; block’s 10 size for 'inside'; equals block’s 10 size "
                                       "+ number of polygons from ‘inside’ = XXX for 'surface'; equals XXX + "
                                       "number of polygons from 'surface' for 'outside'; (Description for 3DO "
                                       "orip file, TNFSSE version has only 9 blocks!)"})
        unk1 = (IntegerBlock(length=4),
                {'is_unknown': True})
        unk2 = (IntegerBlock(length=4),
                {'is_unknown': True})


class NamedIndex(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': '12-bytes record, first 8 bytes is a UTF-8 string, last 4 bytes is an ' \
                                 'unsigned integer (little-endian)',
            'inline_description': True,
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        name = Nfs1Utf8Block(length=8)
        index = IntegerBlock(length=4)


# TODO check additional info in http://3dodev.com/documentation/file_formats/games/nfs
class OripGeometry(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'Geometry block for 3D model with few materials',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (UTF8Block(required_value='ORIP', length=4),
                       {'description': 'Resource ID'})
        block_size = (IntegerBlock(length=4),
                      {'description': 'Total ORIP block size'})
        unk0 = (IntegerBlock(length=4, required_value=0x02BC),
                {'description': 'Looks like always 0x01F4 in 3DO version and 0x02BC in PC TNFSSE. ORIP type?',
                 'is_unknown': True})
        unk1 = (IntegerBlock(length=4, required_value=0),
                {'is_unknown': True})
        vertex_count = (IntegerBlock(length=4),
                        {'description': 'Amount of vertices',
                         'programmatic_value': lambda ctx: len(ctx.data('vertex_block'))})
        unk2 = (BytesBlock(length=4),
                {'is_unknown': True})
        vertex_block_offset = (IntegerBlock(length=4),
                               {'description': 'An offset to vertex_block',
                                'programmatic_value': lambda ctx: ctx.block.offset_to_child_when_packed(
                                    ctx.get_full_data(), 'vertex_block')})
        vertex_uvs_count = (IntegerBlock(length=4),
                            {'description': 'Amount of vertex UV-s (texture coordinates)',
                             'programmatic_value': lambda ctx: len(ctx.data('vertex_uvs_block'))})
        vertex_uvs_block_offset = (IntegerBlock(length=4),
                                   {'description': 'An offset to vertex_uvs_block. Always equals to '
                                                   '`112+polygon_count*12`',
                                    'programmatic_value': lambda ctx: 112 + len(ctx.data('polygons_block')) * 12})
        polygon_count = (IntegerBlock(length=4),
                         {'description': 'Amount of polygons',
                          'programmatic_value': lambda ctx: len(ctx.data('polygons_block'))})
        polygon_block_offset = (IntegerBlock(length=4, is_signed=False, required_value=112),
                                {'description': 'An offset to polygons block'})
        identifier = (UTF8Block(length=12),
                      {'description': 'Some ID of geometry, don\'t know the purpose',
                       'is_unknown': True})
        texture_names_count = (IntegerBlock(length=4),
                               {'description': 'Amount of texture names',
                                'programmatic_value': lambda ctx: len(ctx.data('texture_names_block'))})
        texture_names_block_offset = (IntegerBlock(length=4),
                                      {'description': 'An offset to texture names block. Always equals to '
                                                      '`112+polygon_count*12+vertex_uvs_count*8`',
                                       'programmatic_value': lambda ctx: 112 + len(ctx.data('polygons_block')) * 12
                                                                         + len(ctx.data('vertex_uvs_block')) * 8})
        texture_number_count = (IntegerBlock(length=4),
                                {'description': 'Amount of texture numbers',
                                 'programmatic_value': lambda ctx: len(ctx.data('texture_number_map_block'))})
        texture_number_block_offset = (IntegerBlock(length=4),
                                       {'description': 'An offset to texture numbers block'})
        render_order_count = (IntegerBlock(length=4),
                              {'description': 'Amount of items in render_order block',
                               'programmatic_value': lambda ctx: len(ctx.data('render_order_block'))})
        render_order_block_offset = (IntegerBlock(length=4),
                                     {'description': 'Offset of render_order block. Always equals to '
                                                     '`texture_number_block_offset+texture_number_count*20`',
                                      'programmatic_value': lambda ctx: ctx.data('texture_number_block_offset')
                                                                        + len(
                                          ctx.data('texture_number_map_block')) * 20})
        polygon_vertex_map_block_offset = (IntegerBlock(length=4),
                                           {'description': 'Offset of polygon_vertex_map block',
                                            'programmatic_value': lambda ctx: ctx.block.offset_to_child_when_packed(
                                                ctx.get_full_data(), 'polygon_vertex_map_block')})
        labels0_count = (IntegerBlock(length=4),
                         {'description': 'Amount of items in labels0 block',
                          'programmatic_value': lambda ctx: len(ctx.data('labels0_block'))})
        labels0_block_offset = (IntegerBlock(length=4),
                                {'description': 'Offset of labels0 block. Always equals to `texture_number_block_offset'
                                                '+texture_number_count*20+render_order_count*28`',
                                 'programmatic_value': lambda ctx: ctx.data('texture_number_block_offset')
                                                                   + len(ctx.data('texture_number_map_block')) * 20
                                                                   + len(ctx.data('render_order_block')) * 28})
        labels_count = (IntegerBlock(length=4),
                        {'description': 'Amount of items in labels block',
                         'programmatic_value': lambda ctx: len(ctx.data('labels_block'))})
        labels_block_offset = (IntegerBlock(length=4),
                               {'description': 'Offset of labels block. Always equals to `texture_number_block_offset'
                                               '+texture_number_count*20+render_order_count*28+labels0_count*12`',
                                'programmatic_value': lambda ctx: ctx.data('texture_number_block_offset')
                                                                  + len(ctx.data('texture_number_map_block')) * 20
                                                                  + len(ctx.data('render_order_block')) * 28
                                                                  + len(ctx.data('labels0_block')) * 12})
        unknowns1 = (BytesBlock(length=12),
                     {'is_unknown': True})
        polygons_block = (ArrayBlock(child=OripPolygon(),
                                     length=(lambda ctx: ctx.data('polygon_count'), 'polygon_count')),
                          {'description': 'A block with polygons of the geometry. Probably should be a start '
                                          'point when building model from this file'})
        vertex_uvs_block = (ArrayBlock(child=OripVertexUV(),
                                       length=(lambda ctx: ctx.data('vertex_uvs_count'), 'vertex_uvs_count')),
                            {'description': 'A table of texture coordinates. Items are retrieved by index, '
                                            'located in polygon_vertex_map_block',
                             'custom_offset': 'vertex_uvs_block_offset'})
        texture_names_block = (ArrayBlock(child=OripTextureName(),
                                          length=(lambda ctx: ctx.data('texture_names_count'), 'texture_names_count')),
                               {'description': 'A table of texture references. Items are retrieved by index, '
                                               'located in polygon item',
                                'custom_offset': 'texture_names_block_offset'})
        offset = (BytesBlock(
            length=(lambda ctx: ctx.read_start_offset + ctx.data('texture_number_block_offset') - ctx.buffer.tell(),
                    'space up to offset `texture_number_block_offset`'),
            allow_negative_length=True),
                  {
                      'description': 'In some cases contains unknown data with UTF-8 entries "left_turn", "right_turn", in '
                                     'case of DIABLO.CFM it\'s length is equal to -3, meaning that last 3 bytes from texture'
                                     ' names block are reused by next block'})
        texture_number_map_block = (ArrayBlock(child=ArrayBlock(child=IntegerBlock(length=1), length=20),
                                               length=(lambda ctx: ctx.data('texture_number_count'),
                                                       'texture_number_count')),
                                    {'is_unknown': True,
                                     'custom_offset': 'texture_number_block_offset'})
        render_order_block = (ArrayBlock(child=RenderOrderBlock(),
                                         length=(lambda ctx: ctx.data('render_order_count'), 'render_order_count')),
                              {'description': 'Render order. The exact mechanism how it works is unknown',
                               'custom_offset': 'render_order_block_offset'})
        labels0_block = (ArrayBlock(child=NamedIndex(),
                                    length=(lambda ctx: ctx.data('labels0_count'), 'labels0_count')),
                         {'description': 'Unclear',
                          'custom_offset': 'labels0_block_offset'})
        labels_block = (ArrayBlock(child=NamedIndex(),
                                   length=(lambda ctx: ctx.data('labels_count'), 'labels_count')),
                        {'description': 'Describes tires, smoke and car lights. Smoke effect under the wheel will '
                                        'be displayed on drifting, accelerating and braking in the place where '
                                        'texture is shown. 3DO version ORIP description: "Texture indexes referenced from '
                                        'records in block 10 and block 11th. Texture index shows that wheel '
                                        'or back light will be displayed on the polygon number defined in '
                                        'block 10." - the issue is that TNFSSE orip files consist of 9 blocks',
                         'custom_offset': 'labels_block_offset'})
        vertex_block = (ArrayBlock(child=DelegateBlock(possible_blocks=[Point3D_32_7(), Point3D_32_4()],
                                                       choice_index=lambda ctx: 0 if ctx.buffer.name.endswith(
                                                           '.CFM') else 1),
                                   length=(lambda ctx: ctx.data('vertex_count'), 'vertex_count')),
                        {'description': 'A table of mesh vertices in 3D space. For cars it consists of 32:7 points, '
                                        'else 32:4',
                         'custom_offset': 'vertex_block_offset'})
        polygon_vertex_map_block = (ArrayBlock(child=IntegerBlock(length=4),
                                               length=(lambda ctx: floor((ctx.data(
                                                   'block_size') + ctx.read_start_offset - ctx.buffer.tell()) / 4),
                                                       '?')),
                                    {'description': "A LUT for both 3D and 2D vertices. Every item is an index "
                                                    "of either item in vertex_block or vertex_uvs_block. When "
                                                    "building 3D vertex, polygon defines offset_3d, a lookup to "
                                                    "this table, and value from here is an index of item in "
                                                    "vertex_block. When building UV-s, polygon defines offset_2d,"
                                                    " a lookup to this table, and value from here is an index of "
                                                    "item in vertex_uvs_block",
                                     'custom_offset': 'polygon_vertex_map_block_offset'})
