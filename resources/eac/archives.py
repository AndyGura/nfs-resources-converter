from io import BufferedReader, BytesIO

from parsers.resources.compressed import RefPackArchive, Qfs2Archive, Qfs3Archive
from resources.basic.array_field import ArrayField, ExplicitOffsetsArrayField
from resources.basic.atomic import IntegerField, Utf8Field
from resources.basic.compound_block import CompoundBlock
from resources.basic.delegate_block import DelegateBlock
from resources.basic.literal_block import LiteralResource
from resources.eac.bitmaps import Bitmap16Bit0565, Bitmap24Bit, Bitmap16Bit1555, Bitmap32Bit, Bitmap8Bit, Bitmap4Bit
from resources.eac.geometries import OripGeometry
from resources.eac.palettes import (
    Palette16BitResource,
    Palette32BitResource,
    Palette24BitResource,
    Palette24BitDosResource,
)


class CompressedBlock(DelegateBlock):
    block_description = ''

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.algorithm = None
        self.delegate_block_class = None

    def read(self, buffer: [BufferedReader, BytesIO], size: int, parent_read_data: dict = None):
        uncompressed_bytes = self.algorithm(buffer, size)
        uncompressed = BytesIO(uncompressed_bytes)
        if self.delegate_block_class is None:
            from guess_parser import probe_block_class
            self.delegate_block_class = probe_block_class(uncompressed, self.id + '_UNCOMPRESSED')
        self.delegated_block = self.delegate_block_class()
        return super().read(uncompressed, len(uncompressed_bytes))


class RefPackBlock(CompressedBlock):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.algorithm = RefPackArchive().uncompress


class Qfs2Block(CompressedBlock):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.algorithm = Qfs2Archive().uncompress


class Qfs3Block(CompressedBlock):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.algorithm = Qfs3Archive().uncompress


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
                Bitmap16Bit0565(error_handling_strategy='return'),
                Bitmap4Bit(error_handling_strategy='return'),
                Bitmap8Bit(error_handling_strategy='return'),
                Bitmap32Bit(error_handling_strategy='return'),
                Bitmap16Bit1555(error_handling_strategy='return'),
                Bitmap24Bit(error_handling_strategy='return'),
                Palette24BitDosResource(error_handling_strategy='return'),
                Palette24BitResource(error_handling_strategy='return'),
                Palette32BitResource(error_handling_strategy='return'),
                Palette16BitResource(error_handling_strategy='return'),
            ],
            error_handling_strategy='return',
        ))

    def __getattr__(self, name):
        try:
            return super().__getattr__(name)
        except AttributeError as ex:
            if self.children_descriptions:
                for i, item_name in enumerate(x.name for x in self.children_descriptions):
                    if item_name == name:
                        return self.children[i]
            raise ex

    def _after_children_count_read(self, data, **kwargs):
        self.instance_fields_map['children_descriptions'].length = data['children_count']

    def _after_children_descriptions_read(self, data, **kwargs):
        self.instance_fields_map['children'].offsets = [x.offset + self.initial_buffer_pointer for x in
                                                        data['children_descriptions']]

    def _after_children_read(self, data, **kwargs):
        for i, child in enumerate(data['children']):
            child.id = self._id + ('/' if '__' in self._id else '__') + data['children_descriptions'][i].name


class WwwwArchive(CompoundBlock):
    block_description = ''

    class Fields(CompoundBlock.Fields):
        resource_id = Utf8Field(required_value='wwww', length=4, description='Resource ID')
        children_count = IntegerField(static_size=4, is_signed=False)
        children_offsets = ArrayField(child=IntegerField(static_size=4, is_signed=False))
        children = ExplicitOffsetsArrayField(child=LiteralResource(
            possible_resources=[
                OripGeometry(error_handling_strategy='return'),
                ShpiArchive(error_handling_strategy='return'),
            ],
        ))

    def __getattr__(self, name):
        try:
            return super().__getattr__(name)
        except AttributeError as ex:
            if name.isdigit() and self.children and len(self.children) > int(name):
                return self.children[int(name)]
            raise ex

    def _after_children_count_read(self, data, **kwargs):
        self.instance_fields_map['children_offsets'].length = data['children_count']

    def _after_children_offsets_read(self, data, **kwargs):
        self.instance_fields_map['children'].offsets = [x + self.initial_buffer_pointer for x in
                                                        data['children_offsets']]


WwwwArchive.Fields.children.child.possible_resources.append(WwwwArchive())
WwwwArchive.Fields.children.child.instantiate_kwargs['possible_resources'].append(WwwwArchive())
