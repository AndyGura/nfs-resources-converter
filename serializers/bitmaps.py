from copy import deepcopy

from PIL import Image

from resources.basic.exceptions import SerializationException
from resources.eac.archives import WwwwArchive, ShpiArchive
from resources.eac.bitmaps import AnyBitmapResource
from serializers import BaseFileSerializer


class BitmapSerializer(BaseFileSerializer):

    def serialize(self, block: AnyBitmapResource, path: str):
        super().serialize(block, path)
        Image.frombytes('RGBA',
                        (block.width, block.height),
                        bytes().join([c.to_bytes(4, 'big') for c in block.bitmap])).save(f'{path}.png')


class BitmapWithPaletteSerializer(BaseFileSerializer):

    # def _get_palette_from_wwww(self, wwww: WwwwArchive, max_index=-1, skip_parent_check=False):
    #     if max_index == -1:
    #         max_index = len(wwww.resources)
    #     palette = None
    #     for i in range(max_index - 1, -1, -1):
    #         if isinstance(wwww.resources[i], ShpiArchive):
    #             palette = self._get_palette_from_shpi(wwww.resources[i])
    #             if palette:
    #                 break
    #         elif isinstance(wwww.resources[i], WwwwArchive):
    #             palette = self._get_palette_from_wwww(wwww.resources[i], skip_parent_check=True)
    #             if palette:
    #                 break
    #     if not palette and not skip_parent_check and isinstance(wwww.parent, WwwwArchive):
    #         return self._get_palette_from_wwww(wwww.parent, max_index=wwww.parent.resources.index(wwww))
    #     return palette

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
            from src import require_resource
            # finding in current SHPI directory
            shpi_id = block.id[:max(block.id.rindex('__'), block.id.rindex('/'))]
            palette = require_resource(shpi_id + ('/' if '__' in shpi_id else '__') + '!pal')
            if not palette:
                # some of SHPI directories have upper-cased name of palette. Happens in TNFS track FAM files
                palette = require_resource(shpi_id + ('/' if '__' in shpi_id else '__') + '!PAL')
            if not palette:
                # some of SHPI directories have this. Happens in NFS2SE car models, dash hud, render/pc
                palette = require_resource(shpi_id + ('/' if '__' in shpi_id else '__') + '0000')
                from resources.eac.palettes import BasePalette
                if palette and not isinstance(palette, BasePalette):
                    palette = None
            # TNFS track FAM files contain WWWW directories with SHPI entries, some of them do not have palette, use previous available !pal. 7C bitmap resource data seems to not change as well :(
            # if not palette and isinstance(shpi.parent, WwwwArchive):
            #     palette = self._get_palette_from_wwww(shpi.parent, shpi.parent.resources.index(shpi))
            if palette is None and 'ART/CONTROL/' in block.id:
                # TNFS has QFS files without palette in this directory, and 7C bitmap resource data seems to not differ in this case :(
                from src import require_resource
                palette = require_resource('/'.join(block.id.split('/')[:-1]) + '/CENTRAL.QFS__!pal')
        else:
            palette = block.palette
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
