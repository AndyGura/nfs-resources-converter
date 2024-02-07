from math import floor
from typing import Dict

from library.read_blocks import (DeclarativeCompoundBlock,
                                 UTF8Block,
                                 IntegerBlock,
                                 ArrayBlock,
                                 BytesBlock,
                                 DelegateBlock,
                                 BitFlagsBlock)
from resources.eac.fields.misc import Point3D_32_7, Point3D_32_4


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
                     {'description': "The index in polygon_vmap ORIP's table. This index "
                                     "represents first vertex of this polygon, so in order to determine all "
                                     "vertex we load next 2 or 3 (if quad) indexes from polygon_vertex_map. "
                                     "Look at polygon_vmap description for more info"})
        offset_2d = (IntegerBlock(length=4),
                     {'description': "The same as offset_3d, also points to polygon_vmap, but used "
                                     "for texture coordinates. Look at polygon_vmap description "
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
            'block_description': 'A settings of the texture. From what is known, contains name of bitmap (not always a correct UTF-8)',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        type = BytesBlock(length=8)
        file_name = (UTF8Block(length=4),
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
            'block_description': '12-bytes record, first 8 bytes is a UTF-8 string (sometimes encoding is broken), last'
                                 ' 4 bytes is an unsigned integer (little-endian)',
            'inline_description': True,
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        name = BytesBlock(length=8)
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
        vertices_count = (IntegerBlock(length=4),
                          {'description': 'Amount of vertices',
                           'programmatic_value': lambda ctx: len(ctx.data('vertices'))})
        unk2 = (BytesBlock(length=4),
                {'is_unknown': True})
        vertices_offset = (IntegerBlock(length=4),
                           {'description': 'An offset to vertices',
                            'programmatic_value': lambda ctx: ctx.block.offset_to_child_when_packed(ctx.get_full_data(),
                                                                                                    'vertices')})
        vertex_uvs_count = (IntegerBlock(length=4),
                            {'description': 'Amount of vertex UV-s (texture coordinates)',
                             'programmatic_value': lambda ctx: len(ctx.data('vertex_uvs'))})
        vertex_uvs_offset = (IntegerBlock(length=4),
                             {'description': 'An offset to vertex_uvs. Always equals to `112+polygons_count*12`',
                              'programmatic_value': lambda ctx: 112 + len(ctx.data('polygons')) * 12})
        polygons_count = (IntegerBlock(length=4),
                          {'description': 'Amount of polygons',
                           'programmatic_value': lambda ctx: len(ctx.data('polygons'))})
        polygons_offset = (IntegerBlock(length=4, is_signed=False, required_value=112),
                           {'description': 'An offset to polygons block'})
        identifier = (UTF8Block(length=12),
                      {'description': 'Some ID of geometry, don\'t know the purpose',
                       'is_unknown': True})
        texture_names_count = (IntegerBlock(length=4),
                               {'description': 'Amount of texture names',
                                'programmatic_value': lambda ctx: len(ctx.data('texture_names'))})
        texture_names_offset = (IntegerBlock(length=4),
                                {'description': 'An offset to texture names block. Always equals to '
                                                '`112+polygons_count*12+vertex_uvs_count*8`',
                                 'programmatic_value': lambda ctx: 112 + len(ctx.data('polygons')) * 12
                                                                   + len(ctx.data('vertex_uvs')) * 8})
        texture_numbers_count = (IntegerBlock(length=4),
                                 {'description': 'Amount of texture numbers',
                                  'programmatic_value': lambda ctx: len(ctx.data('texture_numbers'))})
        texture_numbers_offset = (IntegerBlock(length=4),
                                  {'description': 'An offset to texture numbers block'})
        render_orders_count = (IntegerBlock(length=4),
                               {'description': 'Amount of items in render_order block',
                                'programmatic_value': lambda ctx: len(ctx.data('render_orders'))})
        render_orders_offset = (IntegerBlock(length=4),
                                {'description': 'Offset of render_order block. Always equals to '
                                                '`texture_numbers_offset+texture_numbers_count*20`',
                                 'programmatic_value': lambda ctx: ctx.data('texture_numbers_offset')
                                                                   + len(
                                     ctx.data('texture_numbers')) * 20})
        polygon_vmap_offset = (IntegerBlock(length=4),
                               {'description': 'Offset of polygon_vertex_map block',
                                'programmatic_value': lambda ctx: ctx.block.offset_to_child_when_packed(
                                    ctx.get_full_data(), 'polygon_vmap')})
        labels0_count = (IntegerBlock(length=4),
                         {'description': 'Amount of items in labels0 block',
                          'programmatic_value': lambda ctx: len(ctx.data('labels0'))})
        labels0_offset = (IntegerBlock(length=4),
                          {'description': 'Offset of labels0 block. Always equals to `texture_numbers_offset'
                                          '+texture_numbers_count*20+render_orders_count*28`',
                           'programmatic_value': lambda ctx: ctx.data('texture_numbers_offset')
                                                             + len(ctx.data('texture_numbers')) * 20
                                                             + len(ctx.data('render_orders')) * 28})
        labels_count = (IntegerBlock(length=4),
                        {'description': 'Amount of items in labels block',
                         'programmatic_value': lambda ctx: len(ctx.data('labels'))})
        labels_offset = (IntegerBlock(length=4),
                         {'description': 'Offset of labels block. Always equals to `texture_numbers_offset'
                                         '+texture_numbers_count*20+render_orders_count*28+labels0_count*12`',
                          'programmatic_value': lambda ctx: ctx.data('texture_numbers_offset')
                                                            + len(ctx.data('texture_numbers')) * 20
                                                            + len(ctx.data('render_orders')) * 28
                                                            + len(ctx.data('labels0')) * 12})
        unknowns1 = (BytesBlock(length=12),
                     {'is_unknown': True})
        polygons = (ArrayBlock(child=OripPolygon(),
                               length=(lambda ctx: ctx.data('polygons_count'), 'polygons_count')),
                    {'description': 'A block with polygons of the geometry. Probably should be a start point when '
                                    'building model from this file'})
        vertex_uvs = (ArrayBlock(child=OripVertexUV(),
                                 length=(lambda ctx: ctx.data('vertex_uvs_count'), 'vertex_uvs_count')),
                      {'description': 'A table of texture coordinates. Items are retrieved by index, located in '
                                      'polygon_vmap',
                       'custom_offset': 'vertex_uvs_offset'})
        texture_names = (ArrayBlock(child=OripTextureName(),
                                    length=(lambda ctx: ctx.data('texture_names_count'), 'texture_names_count')),
                         {'description': 'A table of texture references. Items are retrieved by index, located in '
                                         'polygon item',
                          'custom_offset': 'texture_names_offset'})
        offset = (BytesBlock(
            length=(lambda ctx: ctx.read_start_offset + ctx.data('texture_numbers_offset') - ctx.buffer.tell(),
                    'space up to offset `texture_numbers_offset`'),
            allow_negative_length=True),
                  {'description': 'In some cases contains unknown data with UTF-8 entries "left_turn", "right_turn", in'
                                  ' case of DIABLO.CFM it\'s length is equal to -3, meaning that last 3 bytes from '
                                  'texture names block are reused by next block'})
        texture_numbers = (ArrayBlock(child=ArrayBlock(child=IntegerBlock(length=1), length=20),
                                      length=(lambda ctx: ctx.data('texture_numbers_count'), 'texture_numbers_count')),
                           {'is_unknown': True,
                            'custom_offset': 'texture_numbers_offset'})
        render_orders = (ArrayBlock(child=RenderOrderBlock(),
                                    length=(lambda ctx: ctx.data('render_orders_count'), 'render_orders_count')),
                         {'description': 'Render order. The exact mechanism how it works is unknown',
                          'custom_offset': 'render_orders_offset'})
        labels0 = (ArrayBlock(child=NamedIndex(),
                              length=(lambda ctx: ctx.data('labels0_count'), 'labels0_count')),
                   {'description': 'Unclear',
                    'custom_offset': 'labels0_offset'})
        labels = (ArrayBlock(child=NamedIndex(),
                             length=(lambda ctx: ctx.data('labels_count'), 'labels_count')),
                  {'description': 'Describes tires, smoke and car lights. Smoke effect under the wheel will be '
                                  'displayed on drifting, accelerating and braking in the place where texture is shown.'
                                  ' 3DO version ORIP description: "Texture indexes referenced from records in block 10 '
                                  'and block 11th. Texture index shows that wheel or back light will be displayed on '
                                  'the polygon number defined in block 10." - the issue is that TNFSSE orip files '
                                  'consist of 9 blocks',
                   'custom_offset': 'labels_offset'})
        vertices = (ArrayBlock(child=DelegateBlock(possible_blocks=[Point3D_32_7(), Point3D_32_4()],
                                                   choice_index=lambda ctx: 0 if ctx.buffer.name.endswith(
                                                       '.CFM') else 1),
                               length=(lambda ctx: ctx.data('vertices_count'), 'vertices_count')),
                    {'description': 'A table of mesh vertices 3D coordinates. For cars uses 32:7 points, else 32:4',
                     'custom_offset': 'vertices_offset'})
        polygon_vmap = (ArrayBlock(child=IntegerBlock(length=4),
                                   length=(lambda ctx: floor(
                                       (ctx.data('block_size') + ctx.read_start_offset - ctx.buffer.tell()) / 4), '?')),
                        {'description': "A LUT for both 3D and 2D vertices. Every item is an index of either item in "
                                        "vertices or vertex_uvs. When building 3D vertex, polygon defines offset_3d, "
                                        "a lookup to this table, and value from here is an index of item in vertices. "
                                        "When building UV-s, polygon defines offset_2d, a lookup to this table, and "
                                        "value from here is an index of item in vertex_uvs",
                         'custom_offset': 'polygon_vmap_offset'})
