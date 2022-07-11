from copy import deepcopy

from PIL import Image

from resources.basic.exceptions import SerializationException
from resources.eac.archives import WwwwArchive, ShpiArchive
from resources.eac.bitmaps import AnyBitmapResource
from resources.eac.geometries import OripGeometry
from resources.eac.palettes import BasePalette
from serializers import BaseFileSerializer


class BitmapSerializer(BaseFileSerializer):

    def serialize(self, block: AnyBitmapResource, path: str):
        super().serialize(block, path)
        Image.frombytes('RGBA',
                        (block.width, block.height),
                        bytes().join([c.to_bytes(4, 'big') for c in block.bitmap])).save(f'{path}.png')


class BitmapWithPaletteSerializer(BaseFileSerializer):

    def _get_palette_from_shpi(self, shpi: ShpiArchive):
        for child in shpi.children:
            print()
        # res = shpi.get_resource_by_name('!pal')
        # if res and isinstance(res, ReadBlockWrapper) and isinstance(res.resource, BasePalette):
        #     return res.resource
        # # some of SHPI directories have upper-cased name of palette. Happens in TNFS track FAM files
        # res = shpi.get_resource_by_name('!PAL')
        # if res and isinstance(res, ReadBlockWrapper) and isinstance(res.resource, BasePalette):
        #     return res.resource
        # # some of SHPI directories have this. Happens in NFS2SE car models, dash hud, render/pc
        # res = shpi.get_resource_by_name('0000')
        # if res and isinstance(res, ReadBlockWrapper) and isinstance(res.resource, BasePalette):
        #     return res.resource
        return None

    def _get_palette_from_wwww(self, wwww: WwwwArchive, max_index=-1, skip_parent_check=False):
        if max_index == -1:
            max_index = len(wwww.resources)
        palette = None
        for i in range(max_index - 1, -1, -1):
            if isinstance(wwww.resources[i], ShpiArchive):
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

    def serialize(self, block: AnyBitmapResource, path: str):
        super().serialize(block, path)
        if (block.palette is None
                or block.palette.resource_id == 0x7C
                or (block.id.endswith('ga00') and 'TR2_001.FAM' in block.id)):
            # need to find the palette, it is a tricky part
            # For textures in FAM files, inline palettes appear to be almost the same as parent palette,
            # sometimes better, sometime worse, the difference is not much noticeable.
            # In case of Autumn Valley fence texture, it totally breaks the picture.
            # If ignore inline palettes in LN32 SHPI, DASH FSH will be broken ¯\_(ツ)_/¯
            # If ignore inline palette in all FAM textures, the train in alpine track will be broken ¯\_(ツ)_/¯
            # autumn valley fence texture broken only in ETRACKFM and NTRACKFM
            # TODO find a generic solution to this problem
            # finding in current SHPI directory
            from src import require_resource
            shpi_id = block.id[:max(block.id.index('__'), block.id.index('/'))]
            palette = require_resource(shpi_id + ('/' if '__' in shpi_id else '__') + '!pal')
            # TNFS has QFS files without palette in this directory, and 7C bitmap resource data seems to not differ in this case :(
            # if not palette and shpi.parent and shpi.parent.name.endswith('CONTROL'):
            #     # TODO load resource here, remove multithreading restriction
            #     try:
            #         main_shpi = shpi.parent.get_resource_by_name('CENTRAL.QFS').uncompressed_resource
            #         palette = self._get_palette_from_shpi(main_shpi)
            #     except Exception:
            #         pass
            # TNFS track FAM files contain WWWW directories with SHPI entries, some of them do not have palette, use previous available !pal. 7C bitmap resource data seems to not change as well :(
            # if not palette and isinstance(shpi.parent, WwwwArchive):
            #     palette = self._get_palette_from_wwww(shpi.parent, shpi.parent.resources.index(shpi))
        else:
            palette = block.palette
        if palette is None and 'ART/CONTROL/' in block.id:
            from src import require_resource
            palette = require_resource('/'.join(block.id.split('/')[:-1]) + '/CENTRAL.QFS__!pal')
        if palette is None:
            raise SerializationException('Palette not found for 8bit bitmap')
        colors = []
        palette_colors = palette.colors
        if block.id[:-4] in ['rsid', 'lite'] and '.CFM' in block.id:
            # NFS1 car tail lights: make transparent
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
