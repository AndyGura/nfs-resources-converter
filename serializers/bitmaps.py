from PIL import Image

import settings
from library.helpers.exceptions import SerializationException
from library.read_data import ReadData
from resources.eac.bitmaps import AnyBitmapBlock, Bitmap8Bit
from resources.utils import determine_palette_for_8_bit_bitmap
from serializers import BaseFileSerializer


class BitmapSerializer(BaseFileSerializer):

    def serialize(self, data: ReadData[AnyBitmapBlock], path: str):
        super().serialize(data, path)
        Image.frombytes('RGBA',
                        (data.width.value, data.height.value),
                        bytes().join([c.to_bytes(4, 'big') for c in data.bitmap])).save(f'{path}.png')


class BitmapWithPaletteSerializer(BaseFileSerializer):

    def serialize(self, data: ReadData[Bitmap8Bit], path: str):
        super().serialize(data, path)
        palette = determine_palette_for_8_bit_bitmap(data)
        if palette is None:
            raise SerializationException('Palette not found for 8bit bitmap')
        colors = []
        palette_colors = [c.value for c in palette.colors]
        if getattr(palette, 'last_color_transparent', False):
            palette_colors[255] = 0
        if data.id[-4:] in ['rsid', 'lite'] and '.CFM' in data.id:
            # NFS1 car tail lights: make transparent
            palette_colors[254] = 0
        for index in data.bitmap:
            try:
                colors.append(palette_colors[index])
            except IndexError:
                colors.append(0)
        Image.frombytes('RGBA',
                        (data.width.value, data.height.value),
                        bytes().join([c.to_bytes(4, 'big') for c in colors])).save(f'{path}.png')
        if settings.images__save_inline_palettes and data.value.palette and data.value.palette == palette:
            from serializers import PaletteSerializer
            palette_serializer = PaletteSerializer()
            palette_serializer.serialize(data.palette, f'{path}_pal')
