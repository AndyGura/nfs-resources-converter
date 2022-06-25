from PIL import Image

from parsers.resources.read_block_wrapper import ReadBlockWrapper
from resources.eac.bitmaps import AnyBitmapResource
from resources.eac.palettes import PaletteReference
from serializers import BaseFileSerializer


class BitmapSerializer(BaseFileSerializer):

    def serialize(self, block: AnyBitmapResource, path: str, wrapper: ReadBlockWrapper):
        super().serialize(block, path, wrapper)
        Image.frombytes('RGBA',
                        (block.width, block.height),
                        bytes().join([c.to_bytes(4, 'big') for c in block.bitmap])).save(f'{path}.png')


class BitmapWithPaletteSerializer(BaseFileSerializer):

    def serialize(self, block: AnyBitmapResource, path: str, wrapper: ReadBlockWrapper):
        super().serialize(block, path, wrapper)
        palette = None
        if isinstance(block.palette.selected_resource, PaletteReference):
            # need to find the palette
            ref_unks = block.palette.unknowns
            if ref_unks == [0, 0, 0, 0, 0, 0, 0]:
                shpi = wrapper.parent
                palette = shpi.get_resource_by_name('!pal').resource
        else:
            palette = block.palette
        if palette is None:
            raise Exception('Palette not found for 8bit bitmap')
        colors = []
        for index in block.bitmap:
            try:
                colors.append(palette.colors[index])
            except IndexError:
                colors.append(0)
        Image.frombytes('RGBA',
                        (block.width, block.height),
                        bytes().join([c.to_bytes(4, 'big') for c in colors])).save(f'{path}.png')
