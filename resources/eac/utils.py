from resources.eac.archives import ShpiBlock, WwwwBlock
from resources.eac.bitmaps import EacPalette


def _get_palette_from_shpi(shpi_block, shpi_data: dict):
    # some of SHPI directories have upper-cased name of palette. Happens in TNFS track FAM files
    # some of SHPI directories have 0000 as palette. Happens in NFS2SE car models, dash hud, render/pc
    child_possible_blocks = shpi_block.field_blocks_map['children'].child.field_blocks_map['item'].possible_blocks
    for name in ['!pal', '!PAL', '0000']:
        try:
            idx = next(i for i, x in enumerate(shpi_data['children']) if x['alias'] == name)
            block = child_possible_blocks[shpi_data['children'][idx]['item']['choice_index']]
            if block and isinstance(block, EacPalette):
                return block, shpi_data['children'][idx]['item']['data']
        except StopIteration:
            pass
    return None, None


def _get_palette_from_wwww(wwww_id, wwww_block: WwwwBlock, wwww_data, max_index=-1, skip_parent_check=False):
    if max_index == -1:
        max_index = len(wwww_data['children'])
    palette_block = None
    palette_data = None
    for i in range(max_index - 1, -1, -1):
        block = wwww_block.item_block.possible_blocks[wwww_data['children'][i]['item']['choice_index']]
        data = wwww_data['children'][i]['item']['data']
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


def determine_palette_for_8_bit_bitmap(block, data: dict, id: str):
    from library import require_resource
    # if not is SHPI
    if id.rfind('__children') == -1 and id.rfind('/children') == -1:
        if data.get('embedded_palette'):
            return EacPalette(), data['embedded_palette']
        return None, None

    shpi_id = id[:max(id.rfind('__children'), id.rfind('/children'))]
    (_, shpi_block, shpi_data), _ = require_resource(shpi_id)
    shpi_child = next(x for x in shpi_data['children'] if x['item']['data'] == data)
    if data.get('embedded_palette') and not (shpi_child['alias'] == 'ga00' and 'TR2_001.FAM' in id):
        return EacPalette(), data['embedded_palette']

    # try to use !pal from shpi
    palette_block, palette_data = _get_palette_from_shpi(shpi_block, shpi_data)
    # need to find the palette, it is a tricky part
    # For textures in FAM files, inline palettes appear to be almost the same as parent palette,
    # sometimes better, sometimes worse, the difference is not much noticeable.
    # In case of Autumn Valley fence texture, it totally breaks the picture.
    # If ignore inline palettes in LN32 SHPI, DASH FSH will be broken ¯\_(ツ)_/¯
    # If ignore inline palette in all FAM textures, the train in alpine track will be broken ¯\_(ツ)_/¯
    # autumn valley fence texture broken only in ETRACKFM and NTRACKFM
    # TNFS track FAM files contain WWWW directories with SHPI entries, some of them do not have palette,
    # use previous available !pal. 7C bitmap resource data seems to not change as well :(
    if not palette_block and '.FAM' in id:
        (parent_id, parent_block, parent_data), _ = require_resource(shpi_id[:shpi_id.rindex('children') - 1])
        (palette_block, palette_data) = _get_palette_from_wwww(parent_id, parent_block, parent_data,
                                                               int(shpi_id.split('/')[-3]))
    if palette_block is None and 'ART/CONTROL/' in id:
        # TNFS has QFS files without palette in this directory, and 7C bitmap resource data seems to not differ in this case :(
        from library import require_resource
        (_, shpi_block, shpi_data), _ = require_resource(
            '/'.join(id.split('__')[0].split('/')[:-1]) + '/CENTRAL.QFS__data')
        (palette_block, palette_data) = _get_palette_from_shpi(shpi_block, shpi_data)

    return palette_block, palette_data


def rotate_list(l, n):
    return l[n:] + l[:n]


def quantize_images_to_8bit(images, num_colors=256):
    """Quantizes one or more RGBA `PIL.Image`s onto a single shared up-to-`num_colors` palette
    (pass a single image to build a palette for just that one). Alpha-0 pixels collapse onto one
    reserved, genuinely-transparent entry; partial alpha is blended towards black and quantized as
    opaque.

    Returns `(indices_per_image, packed_palette_colors)`: per-image 8-bit index lists, and the
    palette as packed internal RGBA ints (`red<<24|green<<16|blue<<8|alpha`) ready for
    `EacPalette`'s `colors.data`."""
    from PIL import Image

    max_width = max(img.width for img in images)
    total_height = sum(img.height for img in images)
    master_image = Image.new("RGB", (max_width, total_height), (0, 0, 0))
    current_y = 0
    contain_transparency = False
    for img in images:
        rgb = Image.new("RGB", img.size, (0, 0, 0))
        rgb.paste(img.convert("RGB"), mask=img.getchannel("A"))
        master_image.paste(rgb, (0, current_y))
        current_y += img.height
        if not contain_transparency:
            contain_transparency = img.getextrema()[3][0] < 255

    reserved_colors = 1 if contain_transparency else 0

    reference_palette_img = master_image.quantize(colors=256 - reserved_colors, method=Image.Quantize.FASTOCTREE)
    rgba_palette_data = reference_palette_img.getpalette("RGBA")[:(num_colors - reserved_colors) * 4]
    if contain_transparency:
        rgba_palette_data += [0, 255, 0, 0]
    rgb_palette_data = []
    for i in range(0, len(rgba_palette_data), 4):
        rgb_palette_data.extend(rgba_palette_data[i:i + 3])
    dummy_palette_img = Image.new("P", (1, 1))
    dummy_palette_img.putpalette(rgb_palette_data, "RGB")

    indices_per_image = []
    for img in images:
        alpha = img.getchannel("A")
        rgb = Image.new("RGB", img.size, (0, 0, 0))
        rgb.paste(img.convert("RGB"), mask=alpha)
        q_img = rgb.quantize(palette=dummy_palette_img)
        data = bytearray(q_img.tobytes())
        if contain_transparency:
            alpha_data = alpha.load()
            w, h = img.size
            k = 0
            for y in range(h):
                for x in range(w):
                    if alpha_data[x, y] == 0:
                        data[k] = 255
                    k += 1
        q_img = Image.frombytes("P", img.size, bytes(data))
        q_img.putpalette(rgba_palette_data, "RGBA")
        indices_per_image.append(list(q_img.get_flattened_data()))

    packed_palette_colors = [
        (rgba_palette_data[i] << 24) | (rgba_palette_data[i + 1] << 16) | (rgba_palette_data[i + 2] << 8)
        | rgba_palette_data[i + 3]
        for i in range(0, len(rgba_palette_data), 4)
    ]
    return indices_per_image, packed_palette_colors


def build_8bit_palette(packed_palette_colors, palette_type, id):
    """Builds an `EacPalette` dict from packed colors (see `quantize_images_to_8bit`), converting
    to `palette_type` if it isn't the native 32-bit format the quantizer produces."""
    pal = EacPalette().new_data()
    pal['resource_id'] = '32Bit color format palette'
    pal['colors']['data'] = packed_palette_colors
    if palette_type != '32Bit color format palette':
        EacPalette().action_convert_format(pal, palette_type, id=id)
    return pal
