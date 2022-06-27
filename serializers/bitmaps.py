from copy import deepcopy

from PIL import Image

from parsers.resources.archives import WwwwArchive, SHPIArchive
from parsers.resources.read_block_wrapper import ReadBlockWrapper
from resources.eac.bitmaps import AnyBitmapResource
from resources.eac.palettes import PaletteReference, BasePalette
from serializers import BaseFileSerializer


class BitmapSerializer(BaseFileSerializer):

    def serialize(self, block: AnyBitmapResource, path: str, wrapper: ReadBlockWrapper):
        super().serialize(block, path, wrapper)
        Image.frombytes('RGBA',
                        (block.width, block.height),
                        bytes().join([c.to_bytes(4, 'big') for c in block.bitmap])).save(f'{path}.png')


def is_tail_lights_texture_for_nfs1_car(wrapper: ReadBlockWrapper):
    from parsers.resources.archives import SHPIArchive
    from parsers.resources.geometries import OripGeometryResource
    return ((wrapper.name in ['rsid', 'lite'])
            and isinstance(wrapper.parent, SHPIArchive)
            and isinstance(wrapper.parent.parent, OripGeometryResource)
            and wrapper.parent.parent.is_car)


class BitmapWithPaletteSerializer(BaseFileSerializer):

    def _get_palette_from_shpi(self, shpi: SHPIArchive):
        res = shpi.get_resource_by_name('!pal')
        if res and isinstance(res, ReadBlockWrapper) and isinstance(res.resource, BasePalette):
            return res.resource
        # some of SHPI directories have upper-cased name of palette. Happens in TNFS track FAM files
        res = shpi.get_resource_by_name('!PAL')
        if res and isinstance(res, ReadBlockWrapper) and isinstance(res.resource, BasePalette):
            return res.resource
        # some of SHPI directories have this. Happens in NFS2SE car models, dash hud, render/pc
        res = shpi.get_resource_by_name('0000')
        if res and isinstance(res, ReadBlockWrapper) and isinstance(res.resource, BasePalette):
            return res.resource
        return None

    def _get_palette_from_wwww(self, wwww: WwwwArchive, max_index=-1, skip_parent_check=False):
        if max_index == -1:
            max_index = len(wwww.resources)
        palette = None
        for i in range(max_index - 1, -1, -1):
            if isinstance(wwww.resources[i], SHPIArchive):
                palette = self._get_palette_from_shpi(wwww.resources[i])
                if palette:
                    break
            elif isinstance(wwww.resources[i], WwwwArchive):
                palette = self._get_palette_from_wwww(wwww.resources[i], skip_parent_check=True)
                if palette:
                    break
        if not palette and not skip_parent_check and isinstance(wwww.parent, WwwwArchive):
            return self._get_palette_from_wwww(wwww.parent, max_index=wwww.parent.resources.index(wwww))
        return palette

    def serialize(self, block: AnyBitmapResource, path: str, wrapper: ReadBlockWrapper):
        super().serialize(block, path, wrapper)
        if (block.palette.selected_resource is None
                or isinstance(block.palette.selected_resource, PaletteReference)
                or (wrapper.name == 'ga00' and wrapper.parent.parent.parent.name == 'TR2_001.FAM')):
            # need to find the palette, it is a tricky part
            # For textures in FAM files, inline palettes appear to be almost the same as parent palette,
            # sometimes better, sometime worse, the difference is not much noticeable.
            # In case of Autumn Valley fence texture, it totally breaks the picture.
            # If ignore inline palettes in LN32 SHPI, DASH FSH will be broken ¯\_(ツ)_/¯
            # If ignore inline palette in all FAM textures, the train in alpine track will be broken ¯\_(ツ)_/¯
            # autumn valley fence texture broken only in ETRACKFM and NTRACKFM
            # TODO find a generic solution to this problem
            shpi = wrapper.parent
            palette = self._get_palette_from_shpi(shpi)
            # TNFS has QFS files without palette in this directory, and 7C bitmap resource data seems to not differ in this case :(
            if not palette and shpi.parent and shpi.parent.name.endswith('CONTROL'):
                # TODO load resource here, remove multithreading restriction
                try:
                    main_shpi = shpi.parent.get_resource_by_name('CENTRAL.QFS').uncompressed_resource
                    palette = self._get_palette_from_shpi(main_shpi)
                except Exception:
                    pass
            # TNFS track FAM files contain WWWW directories with SHPI entries, some of them do not have palette, use previous available !pal. 7C bitmap resource data seems to not change as well :(
            if not palette and isinstance(shpi.parent, WwwwArchive):
                palette = self._get_palette_from_wwww(shpi.parent, shpi.parent.resources.index(shpi))
        else:
            palette = block.palette
        if palette is None:
            raise Exception('Palette not found for 8bit bitmap')
        colors = []
        palette_colors = palette.colors
        if is_tail_lights_texture_for_nfs1_car(wrapper):
            palette_colors = deepcopy(palette_colors)
            palette_colors[254] = 0
        for index in block.bitmap:
            try:
                colors.append(palette_colors[index])
            except IndexError:
                colors.append(0)
        Image.frombytes('RGBA',
                        (block.width, block.height),
                        bytes().join([c.to_bytes(4, 'big') for c in colors])).save(f'{path}.png')
