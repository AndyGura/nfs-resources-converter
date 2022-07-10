from resources.basic.array_field import ArrayField, ExplicitOffsetsArrayField
from resources.basic.atomic import IntegerField, Utf8Field
from resources.basic.compound_block import CompoundBlock
from resources.basic.exceptions import BlockIntegrityException
from resources.basic.literal_block import LiteralResource
from resources.eac.bitmaps import Bitmap16Bit0565, Bitmap24Bit, Bitmap16Bit1555, Bitmap32Bit, Bitmap8Bit, Bitmap4Bit
from resources.eac.fields.misc import Point3D_32_7, Point3D_32_4
from resources.eac.palettes import Palette16BitResource, Palette32BitResource, Palette24BitResource, \
    Palette24BitDosResource


class ShpiChildDescription(CompoundBlock):
    block_description = ''

    class Fields(CompoundBlock.Fields):
        name = Utf8Field(length=4)
        offset = IntegerField(static_size=4, is_signed=False)


class ShpiArchive(CompoundBlock):
    block_description = ''

    class Fields(CompoundBlock.Fields):
        resource_id = Utf8Field(required_value='SHPI', length=4, description='Resource ID')
        length = IntegerField(static_size=4, is_signed=False)
        children_count = IntegerField(static_size=4, is_signed=False)
        shpi_directory = Utf8Field(length=4)
        children_descriptions = ArrayField(child=ShpiChildDescription())
        children = ExplicitOffsetsArrayField(child=LiteralResource(
            possible_resources=[
                Bitmap16Bit0565(),
                Bitmap4Bit(),
                Bitmap8Bit(),
                Bitmap32Bit(),
                Bitmap16Bit1555(),
                Bitmap24Bit(),
                Palette24BitDosResource(),
                Palette24BitResource(),
                Palette32BitResource(),
                Palette16BitResource(),
            ]
        ))

    def _after_children_count_read(self, data, **kwargs):
        self.instance_fields_map['children_descriptions'].length = data['children_count']

    def _after_children_descriptions_read(self, data, **kwargs):
        self.instance_fields_map['children'].offsets = [x.offset + self.initial_buffer_pointer for x in data['children_descriptions']]


