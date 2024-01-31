from resources.eac.archives import ShpiBlock, WwwwBlock
from resources.eac.bitmaps import Bitmap8Bit
from resources.eac.palettes import BasePalette, PaletteReference


def _get_palette_from_shpi(shpi_block, shpi_data: dict):
    # some of SHPI directories have upper-cased name of palette. Happens in TNFS track FAM files
    # some of SHPI directories have 0000 as palette. Happens in NFS2SE car models, dash hud, render/pc
    child_field = shpi_block.field_blocks_map['children'].child
    for name in ['!pal', '!PAL', '0000']:
        try:
            idx = shpi_data['children_aliases'].index(name)
            block = child_field.possible_blocks[shpi_data['children'][idx]['choice_index']]
            if block and isinstance(block, BasePalette):
                return block, shpi_data['children'][idx]['data']
        except ValueError:
            pass
    return None, None


def _get_palette_from_wwww(wwww_id, wwww_block: WwwwBlock, wwww_data, max_index=-1, skip_parent_check=False):
    if max_index == -1:
        max_index = len(wwww_data['children'])
    palette_block = None
    palette_data = None
    for i in range(max_index - 1, -1, -1):
        block = wwww_block.child_block.possible_blocks[wwww_data['children'][i]['choice_index']]
        data = wwww_data['children'][i]['data']
        if isinstance(block, ShpiBlock):
            (palette_block, palette_data) = _get_palette_from_shpi(block, data)
            if palette_block:
                break
        elif isinstance(block, WwwwBlock):
            palette_block, palette_data = _get_palette_from_wwww(None, block, data, skip_parent_check=True)
            if palette_block:
                break
    if not palette_block and not skip_parent_check and 'children' in wwww_id:
        from library import require_resource
        (parent_id, parent_block, parent_data), _ = require_resource(wwww_id[:wwww_id.rindex('children')])
        return _get_palette_from_wwww(parent_id, parent_block, parent_data, max_index=int(wwww_id.split('/')[-3]))
    return palette_block, palette_data


def determine_palette_for_8_bit_bitmap(block: Bitmap8Bit, data: dict, id: str) -> dict:
    from library import require_resource
    palette_data, palette_block = None, None
    shpi_id = id[:max(id.rfind('__children'), id.rfind('/children'))]
    (_, shpi_block, shpi_data), _ = require_resource(shpi_id)
    # in most cases next item in the shpi is the palette without alias in he SHPI header,
    # but I do not know how to interpret PaletteReference resource
    alias = id[max(id.rfind('_children'), id.rfind('/children')) + 10:id.rfind('/data')]
    try:
        next_idx = shpi_data['children_aliases'].index(alias) + 1
    except ValueError as ex:
        # if accessed via array index id
        if alias.isdigit():
            next_idx = int(alias) + 1
            alias = shpi_data['children_aliases'][int(alias)]
        else:
            raise ex
    if next_idx < len(shpi_data['children_aliases']) and shpi_data['children_aliases'][next_idx] is None:
        next_item = shpi_data['children'][next_idx]
        next_item_block = shpi_block.field_blocks_map['children'].child.possible_blocks[next_item['choice_index']]
        if isinstance(next_item_block, BasePalette):
            palette_data, palette_block = next_item['data'], next_item_block
    if (palette_block is None
            or isinstance(palette_block, PaletteReference)
            or (alias == 'ga00' and 'TR2_001.FAM' in id)):
        # try to use !pal from shpi
        palette_block, palette_data = _get_palette_from_shpi(shpi_block, shpi_data)
        # need to find the palette, it is a tricky part
        # For textures in FAM files, inline palettes appear to be almost the same as parent palette,
        # sometimes better, sometime worse, the difference is not much noticeable.
        # In case of Autumn Valley fence texture, it totally breaks the picture.
        # If ignore inline palettes in LN32 SHPI, DASH FSH will be broken ¯\_(ツ)_/¯
        # If ignore inline palette in all FAM textures, the train in alpine track will be broken ¯\_(ツ)_/¯
        # autumn valley fence texture broken only in ETRACKFM and NTRACKFM
        # TNFS track FAM files contain WWWW directories with SHPI entries, some of them do not have palette,
        # use previous available !pal. 7C bitmap resource data seems to not change as well :(
        if not palette_block and '.FAM' in id:
            (parent_id, parent_block, parent_data), _ = require_resource(shpi_id[:shpi_id.rindex('children')])
            (palette_block, palette_data) = _get_palette_from_wwww(parent_id, parent_block, parent_data,
                                                                   int(shpi_id.split('/')[-2]))
        if palette_block is None and 'ART/CONTROL/' in id:
            # TNFS has QFS files without palette in this directory, and 7C bitmap resource data seems to not differ in this case :(
            from library import require_resource
            (_, shpi_block, shpi_data), _ = require_resource(
                '/'.join(id.split('__')[0].split('/')[:-1]) + '/CENTRAL.QFS__data')
            (palette_block, palette_data) = _get_palette_from_shpi(shpi_block, shpi_data)
    return palette_block, palette_data
