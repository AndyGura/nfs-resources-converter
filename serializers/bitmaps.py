from copy import deepcopy

from PIL import Image

from library.read_blocks.exceptions import SerializationException
from resources.eac.archives import WwwwArchive, ShpiArchive
from resources.eac.bitmaps import AnyBitmapBlock
from serializers import BaseFileSerializer


class BitmapSerializer(BaseFileSerializer):

    def serialize(self, block: AnyBitmapBlock, path: str):
        super().serialize(block, path)
        Image.frombytes('RGBA',
                        (block.width, block.height),
                        bytes().join([c.to_bytes(4, 'big') for c in block.bitmap])).save(f'{path}.png')


class BitmapWithPaletteSerializer(BaseFileSerializer):

    def _get_palette_from_shpi(self, shpi: ShpiArchive):
        # some of SHPI directories have upper-cased name of palette. Happens in TNFS track FAM files
        # some of SHPI directories have 0000 as palette. Happens in NFS2SE car models, dash hud, render/pc
        for id in ['!pal', '!PAL', '0000']:
            try:
                palette = getattr(shpi, id)
                from resources.eac.palettes import BasePalette
                if palette and isinstance(palette, BasePalette):
                    return palette
            except AttributeError:
                pass
        return None

    def _get_palette_from_wwww(self, wwww: WwwwArchive, max_index=-1, skip_parent_check=False):
        if max_index == -1:
            max_index = len(wwww.children)
        palette = None
        for i in range(max_index - 1, -1, -1):
            if isinstance(wwww.children[i], ShpiArchive):
                palette = self._get_palette_from_shpi(wwww.children[i])
                if palette:
                    break
            elif isinstance(wwww.children[i], WwwwArchive):
                palette = self._get_palette_from_wwww(wwww.children[i], skip_parent_check=True)
                if palette:
                    break
        if not palette and not skip_parent_check and 'children' in wwww.id:
            from library import require_resource
            parent = require_resource(wwww.id[:wwww.id.rindex('children')])
            return self._get_palette_from_wwww(parent, max_index=next((i for i, x in enumerate(parent.children)
                                                                       if x.id == wwww.id), -1))
        return palette

    def serialize(self, block: AnyBitmapBlock, path: str):
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
            from library import require_resource
            # finding in current SHPI directory
            shpi_id = block.id[:max(block.id.rindex('__'), block.id.rindex('/'))]
            palette = self._get_palette_from_shpi(require_resource(shpi_id))
            # TNFS track FAM files contain WWWW directories with SHPI entries, some of them do not have palette, use previous available !pal. 7C bitmap resource data seems to not change as well :(
            if not palette and '.FAM' in block.id:
                shpi_parent_wwww = require_resource(shpi_id[:shpi_id.rindex('children')])
                palette = self._get_palette_from_wwww(shpi_parent_wwww,
                                                      next((i for i, x in enumerate(shpi_parent_wwww.children)
                                                            if x.id == shpi_id), -1))
            if palette is None and 'ART/CONTROL/' in block.id:
                # TNFS has QFS files without palette in this directory, and 7C bitmap resource data seems to not differ in this case :(
                from library import require_resource
                palette = require_resource('/'.join(block.id.split('/')[:-1]) + '/CENTRAL.QFS__!pal')
        else:
            palette = block.palette
        if palette is None:
            raise SerializationException('Palette not found for 8bit bitmap')
        colors = []
        palette_colors = palette.colors
        if block.id[-4:] in ['rsid', 'lite'] and '.CFM' in block.id:
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
