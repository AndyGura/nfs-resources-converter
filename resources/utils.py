from library.read_data import ReadData
from resources.eac.archives import ShpiBlock, WwwwBlock
from resources.eac.bitmaps import Bitmap8Bit
from resources.eac.palettes import BasePalette


def _get_palette_from_shpi(shpi_block, shpi_data: dict):
    # some of SHPI directories have upper-cased name of palette. Happens in TNFS track FAM files
    # some of SHPI directories have 0000 as palette. Happens in NFS2SE car models, dash hud, render/pc
    child_field = shpi_block.field_blocks_map['children'].child
    for name in ['!pal', '!PAL', '0000']:
        try:
            data = next(x['data'] for x in shpi_data['children'] if x['name'] == name)
            block = child_field.possible_blocks[data['choice_index']]
            if block and isinstance(block, BasePalette):
                return block, data['data']
        except StopIteration:
            pass
    return None, None


def _get_palette_from_wwww(wwww: ReadData[WwwwBlock], max_index=-1, skip_parent_check=False):
    if max_index == -1:
        max_index = len(wwww.children)
    palette_block = None
    palette_data = None
    for i in range(max_index - 1, -1, -1):
        if isinstance(wwww.children[i], ReadData) and isinstance(wwww.children[i].block, ShpiBlock):
            (palette_block, palette_data) = _get_palette_from_shpi(wwww.children[i])
            if palette_block:
                break
        elif isinstance(wwww.children[i], ReadData) and isinstance(wwww.children[i].block, WwwwBlock):
            palette = _get_palette_from_wwww(wwww.children[i], skip_parent_check=True)
            if palette:
                break
    if not palette and not skip_parent_check and 'children' in wwww.id:
        from library import require_resource
        parent, _ = require_resource(wwww.id[:wwww.id.rindex('children')])
        return _get_palette_from_wwww(parent, max_index=next((i for i, x in enumerate(parent.children)
                                                              if x.id == wwww.id), -1))
    return palette


def determine_palette_for_8_bit_bitmap(block: Bitmap8Bit, data: dict, id: str) -> dict:
    embed_palette = data.get('palette')
    palette_block, palette_data = block.field_blocks_map['palette'].possible_blocks[embed_palette['choice_index']], \
    embed_palette['data']
    if (palette_data is None or palette_data['resource_id'] == 0x7C or (id.endswith('ga00') and 'TR2_001.FAM' in id)):
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
        shpi_id = id[:max(id.rfind('__children'), id.rfind('/children'))]
        (_, shpi_block, shpi_data), _ = require_resource(shpi_id)
        (palette_block, palette_data) = _get_palette_from_shpi(shpi_block, shpi_data)
        # TNFS track FAM files contain WWWW directories with SHPI entries, some of them do not have palette, use previous available !pal. 7C bitmap resource data seems to not change as well :(
        if not palette_block and '.FAM' in id:
            shpi_parent_wwww, _ = require_resource(shpi_id[:shpi_id.rindex('children')])
            (palette_block, palette_data) = _get_palette_from_wwww(shpi_parent_wwww,
                                                                   next((i for i, x in
                                                                         enumerate(shpi_parent_wwww['children'])
                                                                         if x.id == shpi_id), -1))
        if palette_block is None and 'ART/CONTROL/' in id:
            # TNFS has QFS files without palette in this directory, and 7C bitmap resource data seems to not differ in this case :(
            from library import require_resource
            (_, shpi_block, shpi_data), _ = require_resource('/'.join(id.split('__')[0].split('/')[:-1]) + '/CENTRAL.QFS__data')
            (palette_block, palette_data) = _get_palette_from_shpi(shpi_block, shpi_data)
    return palette_block, palette_data
