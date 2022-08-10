from resources.eac.palettes import BasePalette
from serializers import BaseFileSerializer


class PaletteSerializer(BaseFileSerializer):

    def serialize(self, data: BasePalette, path: str):
        super().serialize(data, path)
        with open(f'{path}.pal.txt', 'w') as f:
            f.write(f'{data.block.__class__.__name__}\n')
            f.write('Palette used in bitmap serialization. Contains mapping bitmap data bytes to RGBA colors.\n')
            for i, color in enumerate(data.colors):
                f.write(f'\n{hex(i)}:\t#{hex(color.value)}')
