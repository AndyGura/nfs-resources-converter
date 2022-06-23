from resources.base import BaseResource
from resources.fields import RequiredByteField, Int3Field, Int2Field, ArrayField, ByteField
from resources.fields.colors import Color16Bit1555Field


class Bitmap16Bit1555(BaseResource):
    class Fields(BaseResource.Fields):
        resource_id = RequiredByteField(required_value=0x7E, description='Resource ID')
        block_size = Int3Field(description='Bitmap block size 16+2\*width\*height, but not always')
        width = Int2Field(description='Bitmap width in pixels')
        height = Int2Field(description='Bitmap width in pixels')
        unknowns = ArrayField(length=4, child=ByteField(), is_unknown=True)
        x = Int2Field(description='X coordinate of bitmap position on screen. Used for menu/dash sprites')
        y = Int2Field(description='Y coordinate of bitmap position on screen. Used for menu/dash sprites')
        bitmap = ArrayField(child=Color16Bit1555Field(), length=lambda self: self.width * self.height, description='Colors of bitmap pixels')
