from library.context import ReadContext
from library.read_blocks import BytesBlock
from library.exceptions import EndOfBufferException


class TargaImage(BytesBlock):
    def __init__(self):
        super().__init__(length=lambda ctx: ctx.read_bytes_remaining)

    def read(self, ctx: ReadContext, name: str = '', read_bytes_amount=None):
        # inside an archive, the length is the item length passed by the archive, not the rest of the archive
        if read_bytes_amount is None:
            return super().read(ctx, name, read_bytes_amount)
        res = ctx.buffer.read(read_bytes_amount)
        if len(res) < read_bytes_amount:
            raise EndOfBufferException(ctx=ctx.get_or_create_child(name, self))
        return res

    def serializer_class(self):
        from serializers import TargaImageSerializer

        return TargaImageSerializer
