from library.read_blocks.array import ArrayBlock
from library.read_blocks.atomic import IntegerBlock, Utf8Block, BitFlagsBlock
from library.read_blocks.compound import CompoundBlock
from library.read_blocks.literal import LiteralBlock
from resources.eac.fields.misc import Point3D_32_7, Point3D_32_4


class OripPolygon(CompoundBlock):
    block_description = 'A geometry polygon'

    class Fields(CompoundBlock.Fields):
        polygon_type = IntegerBlock(static_size=1,
                                    description="Huh, that's a srange field. From my tests, if it is xxx0_0011, the "
                                                "polygon is a triangle. If xxx0_0100 - it's a quad. Also there is only "
                                                "one polygon for entire TNFS with type == 2 in burnt sienna props. If "
                                                "ignore this polygon everything still looks great")
        mapping = BitFlagsBlock(flag_names=[(0, 'two_sided'),
                                            (1, 'flip_normal'),
                                            (4, 'use_uv')],
                                description='Rendering properties of the polygon')
        texture_index = IntegerBlock(static_size=1, is_signed=False,
                                     description="The index of item in ORIP's texture_names block")
        unk = IntegerBlock(static_size=1)
        offset_3d = IntegerBlock(static_size=4, is_signed=False,
                                 description="The index in polygon_vertex_map_block ORIP's table. This index "
                                             "represents first vertex of this polygon, so in order to determine all "
                                             "vertex we load next 2 or 3 (if quad) indexes from polygon_vertex_map. "
                                             "Look at polygon_vertex_map_block description for more info")
        offset_2d = IntegerBlock(static_size=4, is_signed=False,
                                 description="The same as offset_3d, also points to polygon_vertex_map_block, but used "
                                             "for texture coordinates. Look at polygon_vertex_map_block description "
                                             "for more info")

        unknown_fields = ['unk']


class OripVertexUV(CompoundBlock):
    block_description = 'Texture coordinates for vertex, where each coordinate is: ' \
                        + IntegerBlock(static_size=4, is_signed=False).block_description \
                        + '. The unit is a pixels amount of assigned texture. So it should be changed when selecting ' \
                          'texture with different size'

    def __init__(self, **kwargs):
        kwargs.pop('inline_description', None)
        super().__init__(inline_description=True,
                         **kwargs)

    class Fields(CompoundBlock.Fields):
        u = IntegerBlock(static_size=4, is_signed=True)
        v = IntegerBlock(static_size=4, is_signed=True)


class OripTextureName(CompoundBlock):
    block_description = 'A settings of the texture. From what is known, contains name of bitmap'

    class Fields(CompoundBlock.Fields):
        type = ArrayBlock(child=IntegerBlock(static_size=1), length=4,
                          description='Sometimes UTF8 string, but not always. Unknown purpose')
        unknown0 = ArrayBlock(child=IntegerBlock(static_size=1), length=4)
        file_name = Utf8Block(length=4, description="Name of bitmap in SHPI block")
        unknown1 = ArrayBlock(child=IntegerBlock(static_size=1), length=8)

        unknown_fields = ['type', 'unknown0', 'unknown1']


class RenderOrderBlock(CompoundBlock):
    block_description = ''

    class Fields(CompoundBlock.Fields):
        identifier = Utf8Block(length=8, description="identifier ('NON-SORT', 'inside', 'surface', 'outside')")
        unk0 = IntegerBlock(static_size=4, is_signed=False, description="0x8 for 'NON-SORT' or 0x1 for the others")
        polygons_amount = IntegerBlock(static_size=4, is_signed=False,
                                       description="Polygons amount (3DO). For TNFSSE sometimes too big value")
        polygon_sum = IntegerBlock(static_size=4, is_signed=False,
                                   description="0 for 'NON-SORT'; block’s 10 size for 'inside'; equals block’s 10 size "
                                               "+ number of polygons from ‘inside’ = XXX for 'surface'; equals XXX + "
                                               "number of polygons from 'surface' for 'outside'; (Description for 3DO "
                                               "orip file, TNFSSE version has only 9 blocks!)")
        unk1 = IntegerBlock(static_size=4, is_signed=False)
        unk2 = IntegerBlock(static_size=4, is_signed=False)


# 3DO only http://3dodev.com/documentation/file_formats/games/nfs
# UTF-8 decoding error for TNFSSE cars
# class OripLabelItem(CompoundBlock):
#     block_description = 'Describes tires, smoke and car lights. Smoke effect under the wheel will be displayed on ' \
#                         'drifting, accelerating and braking in the place where texture is shown.'
#
#     class Fields(CompoundBlock.Fields):
#         identifier = Utf8Block(length=8, description="identifier (rt_rear, rt_frnt, bklr, lt_rear, lt_frnt, bkll)")
#         texture_index = IntegerBlock(static_size=2, is_signed=False,
#                                      description="3DO version ORIP description: 'Texture indexes referenced from "
#                                                  "records in block 10 and block 11th. Texture index shows that wheel "
#                                                  "or back light will be displayed on the polygon number defined in "
#                                                  "block 10.' - the issue is that TNFSSE orip files consist of 9 blocks")


class OripGeometry(CompoundBlock):
    block_description = 'Geometry block for 3D model with few materials. The structure is fuzzy and hard to ' \
                        'understand ¯\\\\_(ツ)_/¯. Offsets here can drift, data is not properly' \
                        ' aligned, so it has explicitly defined offsets to some blocks'

    class Fields(CompoundBlock.Fields):
        resource_id = Utf8Block(required_value='ORIP', length=4, description='Resource ID')
        block_size = IntegerBlock(static_size=4, is_signed=False, description='Total ORIP block size')
        unk0 = IntegerBlock(static_size=4, is_signed=False, required_value=0x02BC,
                            description='Looks like always 0x01F4 in 3DO version and 0x02BC in PC TNFSSE. ORIP type?')
        unk1 = IntegerBlock(static_size=4, is_signed=False, required_value=0)
        vertex_count = IntegerBlock(static_size=4, is_signed=False, description='Amount of vertices')
        unknowns0 = ArrayBlock(child=IntegerBlock(static_size=1), length=4)
        vertex_block_offset = IntegerBlock(static_size=4, is_signed=False, description='An offset to vertex_block')
        vertex_uvs_count = IntegerBlock(static_size=4, is_signed=False,
                                        description='Amount of vertex UV-s (texture coordinates)')
        vertex_uvs_block_offset = IntegerBlock(static_size=4, is_signed=False,
                                               description='An offset to vertex_uvs_block')
        polygon_count = IntegerBlock(static_size=4, is_signed=False, description='Amount of polygons')
        polygon_block_offset = IntegerBlock(static_size=4, is_signed=False, description='An offset to polygons block')
        identifier = Utf8Block(length=12, description='Some ID of geometry, don\'t know the purpose')
        texture_names_count = IntegerBlock(static_size=4, is_signed=False, description='Amount of texture names')
        texture_names_block_offset = IntegerBlock(static_size=4, is_signed=False,
                                                  description='An offset to texture names block')
        texture_number_count = IntegerBlock(static_size=4, is_signed=False, description='Amount of texture numbers')
        texture_number_block_offset = IntegerBlock(static_size=4, is_signed=False,
                                                   description='An offset to texture numbers block')
        render_order_count = IntegerBlock(static_size=4, is_signed=False,
                                          description='Amount of items in render_order block')
        render_order_block_offset = IntegerBlock(static_size=4, is_signed=False,
                                                 description='Offset of render_order block')
        polygon_vertex_map_block_offset = IntegerBlock(static_size=4, is_signed=False,
                                                       description='Offset of polygon_vertex_map block')
        unk0_count = IntegerBlock(static_size=4, is_signed=False, description='Amount of items in unk1 block')
        unk0_block_offset = IntegerBlock(static_size=4, is_signed=False, description='Offset of unk1 block')
        labels_count = IntegerBlock(static_size=4, is_signed=False, description='Amount of items in labels block')
        labels_block_offset = IntegerBlock(static_size=4, is_signed=False, description='Offset of labels block')
        unknowns1 = ArrayBlock(child=IntegerBlock(static_size=1), length=12)
        polygons_block = ArrayBlock(child=OripPolygon(), length_label="polygon_count",
                                    description='A block with polygons of the geometry. Probably should be a start '
                                                'point when building model from this file')
        vertex_uvs_block = ArrayBlock(child=OripVertexUV(), length_label="vertex_uvs_count",
                                      description='A table of texture coordinates. Items are retrieved by index, '
                                                  'located in polygon_vertex_map_block')
        texture_names_block = ArrayBlock(child=OripTextureName(), length_label="texture_names_count",
                                         description='A table of texture references. Items are retrieved by index, '
                                                     'located in polygon item')
        texture_number_map_block = ArrayBlock(child=ArrayBlock(child=IntegerBlock(static_size=1), length=20),
                                              length_label="texture_number_count")
        render_order_block = ArrayBlock(child=RenderOrderBlock(), length_label="render_order_count",
                                        description='Render order. The exact mechanism how it works is unknown')
        unk0_block = ArrayBlock(child=ArrayBlock(child=IntegerBlock(static_size=1), length=12),
                                length_label="unk1_count")
        labels_block = ArrayBlock(child=ArrayBlock(child=IntegerBlock(static_size=1), length=12),
                                  length_label="labels_count",
                                  description='Format and purpose is unknown. 3DO spec available here: http://3dodev.'
                                              'com/documentation/file_formats/games/nfs , but do not work for TNFSSE: '
                                              'UTF-8 decode error')
        vertex_block = ArrayBlock(child=LiteralBlock(
            possible_resources=[Point3D_32_7(), Point3D_32_4()]),
            length_label="vertex_count",
            description='A table of mesh vertices in 3D space. For cars it consists of 32:7 points, else 32:4')
        polygon_vertex_map_block = ArrayBlock(child=IntegerBlock(static_size=4), length_label="(up to end of block)",
                                              length_strategy="read_available",
                                              description="A LUT for both 3D and 2D vertices. Every item is an index "
                                                          "of either item in vertex_block or vertex_uvs_block. When "
                                                          "building 3D vertex, polygon defines offset_3d, a lookup to "
                                                          "this table, and value from here is an index of item in "
                                                          "vertex_block. When building UV-s, polygon defines offset_2d,"
                                                          " a lookup to this table, and value from here is an index of "
                                                          "item in vertex_uvs_block")

        unknown_fields = ['unk0', 'unk1', 'unknowns0', 'identifier', 'unknowns1', 'texture_number_map_block',
                          'unk0_block', 'labels_block']

    def _after_unknowns1_read(self, data, buffer, state, **kwargs):
        if not state.get('polygons_block'):
            state['polygons_block'] = {}
        state['polygons_block']['length'] = data['polygon_count'].value
        if not state.get('vertex_uvs_block'):
            state['vertex_uvs_block'] = {}
        state['vertex_uvs_block']['length'] = data['vertex_uvs_count'].value
        if not state.get('texture_names_block'):
            state['texture_names_block'] = {}
        state['texture_names_block']['length'] = data['texture_names_count'].value
        if not state.get('texture_number_map_block'):
            state['texture_number_map_block'] = {}
        state['texture_number_map_block']['length'] = data['texture_number_count'].value
        if not state.get('render_order_block'):
            state['render_order_block'] = {}
        state['render_order_block']['length'] = data['render_order_count'].value
        if not state.get('unk0_block'):
            state['unk0_block'] = {}
        state['unk0_block']['length'] = data['unk0_count'].value
        if not state.get('labels_block'):
            state['labels_block'] = {}
        state['labels_block']['length'] = data['labels_count'].value
        if not state.get('vertex_block'):
            state['vertex_block'] = {}
        state['vertex_block']['length'] = data['vertex_count'].value
        if not state['vertex_block'].get('common_children_states'):
            state['vertex_block']['common_children_states'] = {}
        state['vertex_block']['common_children_states']['delegated_block'] = (Point3D_32_7()
                                                                              if buffer.name.endswith('.CFM')
                                                                              else Point3D_32_4())

    def _before_polygons_block_read(self, data, buffer, initial_buffer_pointer, **kwargs):
        buffer.seek(initial_buffer_pointer + data['polygon_block_offset'].value)

    def _before_vertex_uvs_block_read(self, data, buffer, initial_buffer_pointer, **kwargs):
        buffer.seek(initial_buffer_pointer + data['vertex_uvs_block_offset'].value)

    def _before_texture_names_block_read(self, data, buffer, initial_buffer_pointer, **kwargs):
        buffer.seek(initial_buffer_pointer + data['texture_names_block_offset'].value)

    def _before_texture_number_map_block_read(self, data, buffer, initial_buffer_pointer, **kwargs):
        buffer.seek(initial_buffer_pointer + data['texture_number_block_offset'].value)

    def _before_render_order_block_read(self, data, buffer, initial_buffer_pointer, **kwargs):
        buffer.seek(initial_buffer_pointer + data['render_order_block_offset'].value)

    def _before_unk0_block_read(self, data, buffer, initial_buffer_pointer, **kwargs):
        buffer.seek(initial_buffer_pointer + data['unk0_block_offset'].value)

    def _before_labels_block_read(self, data, buffer, initial_buffer_pointer, **kwargs):
        buffer.seek(initial_buffer_pointer + data['labels_block_offset'].value)

    def _before_vertex_block_read(self, data, buffer, initial_buffer_pointer, **kwargs):
        buffer.seek(initial_buffer_pointer + data['vertex_block_offset'].value)

    def _before_polygon_vertex_map_block_read(self, data, buffer, initial_buffer_pointer, **kwargs):
        buffer.seek(initial_buffer_pointer + data['polygon_vertex_map_block_offset'].value)
