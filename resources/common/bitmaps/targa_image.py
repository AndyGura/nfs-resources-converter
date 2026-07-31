from library.read_blocks import BytesBlock


class TargaImage(BytesBlock):

    def __init__(self):
        super().__init__(length=lambda ctx: ctx.read_bytes_remaining)

    def serializer_class(self):
        from serializers import TargaImageSerializer
        return TargaImageSerializer
