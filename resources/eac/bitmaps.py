from resources.base import BaseResource, LiteralResource
from resources.eac import palettes
from resources.fields import RequiredByteField, Int3Field, Int2Field, ArrayField, ByteField
from resources.fields.colors import (
    Color16Bit1555Field,
    Color16Bit0565Field,
    Color32BitField,
    Color24BitLittleEndianField
)


class AnyBitmapResource:

    def _after_height_read(self, data, total_size, **kwargs):
        pixel_size = self.instance_fields_map['bitmap'].child.size
        block_size = data['block_size']
        expected_block_size = pixel_size * data['width'] * data['height'] + 16
        if block_size == 0:
            # some NFS2 resources have block size equal to 0
            block_size = expected_block_size
        trailing_bytes_length = total_size - block_size
        if trailing_bytes_length < 0:
            raise Exception(
                f'Too big bitmap block size {block_size}, available: {total_size}. Expected block size {expected_block_size}')
        self.instance_fields_map['bitmap'].length = data['width'] * data['height']


class Bitmap16Bit0565(AnyBitmapResource, BaseResource):
    class Fields(BaseResource.Fields):
        resource_id = RequiredByteField(required_value=0x78, description='Resource ID')
        block_size = Int3Field(description='Bitmap block size 16+2\\*width\\*height, but not always')
        width = Int2Field(description='Bitmap width in pixels')
        height = Int2Field(description='Bitmap width in pixels')
        unknowns = ArrayField(length=4, child=ByteField(), is_unknown=True)
        x = Int2Field(description='X coordinate of bitmap position on screen. Used for menu/dash sprites')
        y = Int2Field(description='Y coordinate of bitmap position on screen. Used for menu/dash sprites')
        bitmap = ArrayField(child=Color16Bit0565Field(), length_label='<width * height>',
                            description='Colors of bitmap pixels')


class Bitmap8Bit(AnyBitmapResource, BaseResource):
    # TODO write description
    class Fields(BaseResource.Fields):
        resource_id = RequiredByteField(required_value=0x7B, description='Resource ID')
        block_size = Int3Field(description='Bitmap block size 16+2\\*width\\*height, but not always')
        width = Int2Field(description='Bitmap width in pixels')
        height = Int2Field(description='Bitmap width in pixels')
        unknowns = ArrayField(length=4, child=ByteField(), is_unknown=True)
        x = Int2Field(description='X coordinate of bitmap position on screen. Used for menu/dash sprites')
        y = Int2Field(description='Y coordinate of bitmap position on screen. Used for menu/dash sprites')
        bitmap = ArrayField(child=ByteField(), length_label='<width * height>',
                            description='Color indexes of bitmap pixels. The actual colors are '
                                        'in assigned to this bitmap palette')
        palette = LiteralResource(possible_resources=[palettes.PaletteReference(),
                                                      palettes.Palette24BitDosResource(),
                                                      palettes.Palette24BitResource(),
                                                      palettes.Palette32BitResource(),
                                                      palettes.Palette16BitResource(),
                                                      ],
                                  is_optional=True,
                                  description='Palette, assigned to this bitmap or reference to external palette?. '
                                              'The exact mechanism of choosing the correct palette '
                                              '(except embedded one) is unknown')


class Bitmap32Bit(AnyBitmapResource, BaseResource):
    class Fields(BaseResource.Fields):
        resource_id = RequiredByteField(required_value=0x7D, description='Resource ID')
        block_size = Int3Field(description='Bitmap block size 16+2\\*width\\*height, but not always')
        width = Int2Field(description='Bitmap width in pixels')
        height = Int2Field(description='Bitmap width in pixels')
        unknowns = ArrayField(length=4, child=ByteField(), is_unknown=True)
        x = Int2Field(description='X coordinate of bitmap position on screen. Used for menu/dash sprites')
        y = Int2Field(description='Y coordinate of bitmap position on screen. Used for menu/dash sprites')
        bitmap = ArrayField(child=Color32BitField(), length_label='<width * height>',
                            description='Colors of bitmap pixels')


class Bitmap16Bit1555(AnyBitmapResource, BaseResource):
    class Fields(BaseResource.Fields):
        resource_id = RequiredByteField(required_value=0x7E, description='Resource ID')
        block_size = Int3Field(description='Bitmap block size 16+2\\*width\\*height, but not always')
        width = Int2Field(description='Bitmap width in pixels')
        height = Int2Field(description='Bitmap width in pixels')
        unknowns = ArrayField(length=4, child=ByteField(), is_unknown=True)
        x = Int2Field(description='X coordinate of bitmap position on screen. Used for menu/dash sprites')
        y = Int2Field(description='Y coordinate of bitmap position on screen. Used for menu/dash sprites')
        bitmap = ArrayField(child=Color16Bit1555Field(), length_label='<width * height>',
                            description='Colors of bitmap pixels')


class Bitmap24Bit(AnyBitmapResource, BaseResource):
    class Fields(BaseResource.Fields):
        resource_id = RequiredByteField(required_value=0x7F, description='Resource ID')
        block_size = Int3Field(description='Bitmap block size 16+2\\*width\\*height, but not always')
        width = Int2Field(description='Bitmap width in pixels')
        height = Int2Field(description='Bitmap width in pixels')
        unknowns = ArrayField(length=4, child=ByteField(), is_unknown=True)
        x = Int2Field(description='X coordinate of bitmap position on screen. Used for menu/dash sprites')
        y = Int2Field(description='Y coordinate of bitmap position on screen. Used for menu/dash sprites')
        bitmap = ArrayField(child=Color24BitLittleEndianField(), length_label='<width * height>',
                            description='Colors of bitmap pixels')
