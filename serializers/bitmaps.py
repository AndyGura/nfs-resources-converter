from PIL import Image

from parsers.resources.archives import WwwwArchive, SHPIArchive
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

    def _get_palette_from_shpi(self, shpi: SHPIArchive):
        try:
            return shpi.get_resource_by_name('!pal').resource
        except:
            pass
        # some of SHPI directories have upper-cased name of palette. Happens in TNFS track FAM files
        try:
            return shpi.get_resource_by_name('!PAL').resource
        except:
            pass
        return None


    def serialize(self, block: AnyBitmapResource, path: str, wrapper: ReadBlockWrapper):
        super().serialize(block, path, wrapper)
        palette = None
        if block.palette.selected_resource is None or isinstance(block.palette.selected_resource, PaletteReference):
            # need to find the palette
            # FIXME test logic to filter out other palette location cases
            ref_unks = block.palette.unknowns if block.palette.selected_resource else [0, 0, 0, 0, 0, 0, 0]
            if (
                    ref_unks == [0, 0, 0, 0, 0, 0, 0]
                    or ref_unks == [0, 0, 0, 6, 0, 0, 0]
                    or ref_unks == [0, 0, 0, 8, 0, 0, 0]
                    or ref_unks == [0, 0, 0, 9, 0, 0, 0]
                    or ref_unks == [0, 0, 0, 10, 0, 0, 0]
                    or ref_unks == [0, 0, 0, 11, 0, 0, 0]
                    or ref_unks == [0, 0, 0, 20, 0, 0, 0]
            ):
                shpi = wrapper.parent
                palette = self._get_palette_from_shpi(shpi)
                # TNFS has QFS files without palette in this directory, and 7C bitmap resource data seems to not differ in this case :(
                if not palette and ref_unks == [0, 0, 0, 0, 0, 0, 0] and shpi.parent and shpi.parent.name.endswith('CONTROL'):
                    # TODO load resource here, remove multithreading restriction
                    try:
                        main_shpi = shpi.parent.get_resource_by_name('CENTRAL.QFS').uncompressed_resource
                        palette = self._get_palette_from_shpi(main_shpi)
                    except Exception:
                        pass
                # TNFS track FAM files contain WWWW directories with SHPI entries, some of them do not have palette, use previous available !pal. 7C bitmap resource data seems to not change as well :(
                if not palette and ref_unks == [0, 0, 0, 0, 0, 0, 0] and isinstance(shpi.parent, WwwwArchive):
                    my_shpi_index = shpi.parent.resources.index(shpi)
                    for i in range(my_shpi_index - 1, -1, -1):
                        palette = self._get_palette_from_shpi(shpi.parent.resources[i])
                        if palette:
                            break
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
