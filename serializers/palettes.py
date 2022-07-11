from parsers.resources.read_block_wrapper import ReadBlockWrapper
from resources.eac.palettes import BasePalette
from serializers import BaseFileSerializer


class PaletteSerializer(BaseFileSerializer):

    def serialize(self, block: BasePalette, path: str):
        super().serialize(block, path)
        with open(f'{path}.pal.txt', 'w') as f:
            f.write(f'{block.__class__.__name__.replace("Resource", "")}\n')
            f.write('Palette used in bitmap serialization. Contains mapping bitmap data bytes to RGBA colors.\n')
            for i, color in enumerate(block.colors):
                f.write(f'\n{hex(i)}:\t#{hex(color)}')
