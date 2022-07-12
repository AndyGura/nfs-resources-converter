from resources.basic.array_field import ArrayField
from resources.basic.atomic import IntegerField, Utf8Field
from resources.basic.compound_block import CompoundBlock
from resources.basic.exceptions import BlockIntegrityException
from resources.basic.literal_block import LiteralResource
from resources.eac.fields.misc import Point3D_32_7, Point3D_32_4


class OripPolygon(CompoundBlock):
    block_description = ''

    class Fields(CompoundBlock.Fields):
        polygon_type = IntegerField(static_size=1)
        normal = IntegerField(static_size=1)
        texture_index = IntegerField(static_size=1, is_signed=False)
        unk = IntegerField(static_size=1, is_unknown=True)
        offset_3d = IntegerField(static_size=4, is_signed=False)
        offset_2d = IntegerField(static_size=4, is_signed=False)


class OripVertexUV(CompoundBlock):
    block_description = 'Texture coordinates for vertex, where each coordinate is: ' \
                        + IntegerField(static_size=4, is_signed=False).block_description \
                        + '. The unit is a pixels amount of assigned texture. So it should be changed when selecting ' \
                          'texture with different size'

    def __init__(self, **kwargs):
        kwargs['inline_description'] = True
        super().__init__(**kwargs)

    class Fields(CompoundBlock.Fields):
        u = IntegerField(static_size=4, is_signed=True)
        v = IntegerField(static_size=4, is_signed=True)


class OripTextureName(CompoundBlock):
    block_description = ''  # TODO

    def __init__(self, **kwargs):
        kwargs['inline_description'] = True
        super().__init__(**kwargs)

    class Fields(CompoundBlock.Fields):
        type = ArrayField(child=IntegerField(static_size=1), length=4, is_unknown=True,
                          description='Sometimes UTF8 string, but not always')
        unknown0 = ArrayField(child=IntegerField(static_size=1), length=4, is_unknown=True)
        file_name = Utf8Field(length=4)
        unknown1 = ArrayField(child=IntegerField(static_size=1), length=8, is_unknown=True)


class OripGeometry(CompoundBlock):
    block_description = 'Geometry block for 3D model with few materials'

    class Fields(CompoundBlock.Fields):
        resource_id = Utf8Field(required_value='ORIP', length=4, description='Resource ID')
        unknowns0 = ArrayField(child=IntegerField(static_size=1), length=12, is_unknown=True)
        vertex_count = IntegerField(static_size=4, is_signed=False)
        unknowns1 = ArrayField(child=IntegerField(static_size=1), length=4, is_unknown=True)
        vertex_block_offset = IntegerField(static_size=4, is_signed=False)
        vertex_uvs_count = IntegerField(static_size=4, is_signed=False)
        vertex_uvs_block_offset = IntegerField(static_size=4, is_signed=False)
        polygon_count = IntegerField(static_size=4, is_signed=False)
        polygon_block_offset = IntegerField(static_size=4, is_signed=False)
        identifier = Utf8Field(length=12)
        texture_names_count = IntegerField(static_size=4, is_signed=False)
        texture_names_block_offset = IntegerField(static_size=4, is_signed=False)
        texture_number_count = IntegerField(static_size=4, is_signed=False)
        texture_number_block_offset = IntegerField(static_size=4, is_signed=False)
        unk0_count = IntegerField(static_size=4, is_signed=False)
        unk0_block_offset = IntegerField(static_size=4, is_signed=False)
        polygon_vertex_map_block_offset = IntegerField(static_size=4, is_signed=False)
        unk1_count = IntegerField(static_size=4, is_signed=False)
        unk1_block_offset = IntegerField(static_size=4, is_signed=False)
        labels_count = IntegerField(static_size=4, is_signed=False)
        labels_block_offset = IntegerField(static_size=4, is_signed=False)
        unknowns2 = ArrayField(child=IntegerField(static_size=1), length=12, is_unknown=True)
        polygons_block = ArrayField(child=OripPolygon())
        vertex_uvs_block = ArrayField(child=OripVertexUV())
        texture_names_block = ArrayField(child=OripTextureName())
        texture_number_map_block = ArrayField(child=ArrayField(child=IntegerField(static_size=1), length=20),
                                              is_unknown=True)
        unk0_block = ArrayField(child=ArrayField(child=IntegerField(static_size=1), length=28), is_unknown=True)
        unk1_block = ArrayField(child=ArrayField(child=IntegerField(static_size=1), length=12), is_unknown=True)
        labels_block = ArrayField(child=ArrayField(child=IntegerField(static_size=1), length=12), is_unknown=True)
        vertex_block = ArrayField(child=LiteralResource(
            possible_resources=[Point3D_32_7(), Point3D_32_4()]),
            description='Mesh vertices. For cars it is 32:7 point, else 32:4')
        polygon_vertex_map_block = ArrayField(child=IntegerField(static_size=4), length_strategy="read_available")

    def _after_unknowns2_read(self, data, buffer, **kwargs):
        self.instance_fields_map['polygons_block'].length = data['polygon_count']
        self.instance_fields_map['vertex_uvs_block'].length = data['vertex_uvs_count']
        self.instance_fields_map['texture_names_block'].length = data['texture_names_count']
        self.instance_fields_map['texture_number_map_block'].length = data['texture_number_count']
        self.instance_fields_map['unk0_block'].length = data['unk0_count']
        self.instance_fields_map['unk1_block'].length = data['unk1_count']
        self.instance_fields_map['labels_block'].length = data['labels_count']
        self.instance_fields_map['vertex_block'].length = data['vertex_count']
        self.instance_fields_map['vertex_block'].child = (Point3D_32_7()
                                                          if buffer.name.endswith('.CFM')
                                                          else Point3D_32_4())

    def _before_polygons_block_read(self, data, buffer, **kwargs):
        buffer.seek(self.initial_buffer_pointer + data['polygon_block_offset'])

    def _before_vertex_uvs_block_read(self, data, buffer, **kwargs):
        buffer.seek(self.initial_buffer_pointer + data['vertex_uvs_block_offset'])

    def _before_texture_names_block_read(self, data, buffer, **kwargs):
        buffer.seek(self.initial_buffer_pointer + data['texture_names_block_offset'])

    def _before_texture_number_map_block_read(self, data, buffer, **kwargs):
        buffer.seek(self.initial_buffer_pointer + data['texture_number_block_offset'])

    def _before_unk0_block_read(self, data, buffer, **kwargs):
        buffer.seek(self.initial_buffer_pointer + data['unk0_block_offset'])

    def _before_unk1_block_read(self, data, buffer, **kwargs):
        buffer.seek(self.initial_buffer_pointer + data['unk1_block_offset'])

    def _before_labels_block_read(self, data, buffer, **kwargs):
        buffer.seek(self.initial_buffer_pointer + data['labels_block_offset'])

    def _before_vertex_block_read(self, data, buffer, **kwargs):
        buffer.seek(self.initial_buffer_pointer + data['vertex_block_offset'])

    def _before_polygon_vertex_map_block_read(self, data, buffer, **kwargs):
        buffer.seek(self.initial_buffer_pointer + data['polygon_vertex_map_block_offset'])