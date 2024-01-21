from serializers import BaseFileSerializer


class PaletteSerializer(BaseFileSerializer):

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs):
        super().serialize(data, path, is_dir=False, id=id, block=block)
        with open(f'{path}.pal.txt', 'w') as f:
            f.write(f'{block.__class__.__name__}\n')
            f.write('Palette used in bitmap serialization. Contains mapping bitmap data bytes to RGBA colors.\n')
            for i, color in enumerate(data['colors']):
                f.write(f'\n{hex(i)}:\t#{hex(color)}')
