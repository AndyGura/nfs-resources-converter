from PIL import Image

from resources.eac.bitmaps import AnyBitmapResource
from serializers import BaseFileSerializer


class BitmapSerializer(BaseFileSerializer):

    def serialize(self, block: AnyBitmapResource, path: str):
        super().serialize(block, path)
        Image.frombytes('RGBA',
                        (block.width, block.height),
                        bytes().join([c.to_bytes(4, 'big') for c in block.bitmap])).save(f'{path}.png')


class BitmapWithPaletteSerializer(BaseFileSerializer):

    def serialize(self, block: AnyBitmapResource, path: str):
        super().serialize(block, path)
        colors = []
        for index in block.bitmap:
            try:
                colors.append(block.palette.colors[index])
            except IndexError:
                colors.append(0)
        Image.frombytes('RGBA',
                        (block.width, block.height),
                        bytes().join([c.to_bytes(4, 'big') for c in colors])).save(f'{path}.png')
