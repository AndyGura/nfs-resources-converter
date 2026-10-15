"""`car_colors.json` of a TNFS car model (CFM): the colors the game puts in place of some palette indices of the car
textures, as replacements of colors of the exported PNGs (nfs-web and the GUI recolor the PNGs, they never read
palettes). Data of Win95 SE (`gfx_car_palettes_setup` 0x4572e0, `gfx_shpi_remap_to_vga_palette` 0x4470e0,
`gfx_draw_car_model` 0x458d4c), 6-bit VGA colors (0..63 per component), written as the converter writes 24BitDos
palettes (value << 2)"""

from typing import Dict, List, Optional, Tuple

TAIL_LIGHT_INDEX = 254
LIGHT_BAR_INDICES = [250, 251, 252, 253]

# car_model_id of the racers by CFM name (name table 0x4c5660); an M*.CFM model has the id of its car
RACER_MODEL_IDS = {
    'TSUPRA': 0,
    'LDIABL': 1,
    'P911': 2,
    'CZR1': 3,
    'F512TR': 4,
    'DVIPER': 5,
    'ANSX': 6,
    'MRX7': 7,
    'TRAFFC': 11,
}
# VGA palette entries of a car taken from the start of its `!xxx` (g_car_palette_slot_count 0x4c56f8): player and
# opponent 23 (+ 1 for the player in a single race / tournament), traffic 8
PALETTE_SLICE = 24

# tail light colors by car_model_id: g_tail_light_colours 0x4c578c (unlit), g_tail_light_colours_lit 0x4c57b3 (while
# `brake` >= 0xb). Traffic and cop cars have no tail light entry of their own: their index 254 keeps the one of the
# car remapped before them (the opponent's), so they get the colors most racers have, as an unknown car does
TAIL_LIGHTS_OFF_DEFAULT = (15, 3, 3)
TAIL_LIGHTS_ON_DEFAULT = (62, 5, 5)
TAIL_LIGHTS_OFF = {4: (6, 6, 6), 11: (30, 5, 5)}
TAIL_LIGHTS_ON = {1: (47, 5, 5), 11: (62, 20, 20)}

# the cop's light bar (indices 250..253 remapped to VGA entries 0xfa..0xfd): g_siren_colours 0x4c5610, swapped with
# g_siren_colours_swapped 0x4c561c every 16 clock units (60 per second) during a police chase. The game makes the car of
# slot 2 the cop (COPMUST in head-to-head), not anything in the file; other cars get these indices black
SIREN_COLORS = [(63, 0, 32), (48, 0, 16), (32, 0, 63), (16, 0, 48)]
SIREN_COLORS_SWAPPED = [(32, 0, 63), (16, 0, 48), (63, 0, 32), (48, 0, 16)]
SIREN_SWAP_INTERVAL_MS = 16 * 1000 / 60


def car_texture_palette(colors: List[int]) -> List[int]:
    """Palette (internal RGBA ints) a CFM texture is exported with: the colors of the indices the game replaces (250..254)
    made unique in the palette, so that replacing a PNG color changes these pixels only. A color shared with another
    entry gets the nearest free one (blue, then green, then red moved by 1, 2...); the files have no such color"""
    colors = list(colors)
    for i in LIGHT_BAR_INDICES + [TAIL_LIGHT_INDEX]:
        if i >= len(colors):
            break
        taken = {c >> 8 for j, c in enumerate(colors) if j != i}
        rgb, alpha = colors[i] >> 8, colors[i] & 0xFF
        if rgb not in taken:
            continue
        candidates = (
            rgb + sign * step * (1 << shift)
            for step in range(1, 256)
            for shift in (0, 8, 16)
            for sign in (1, -1)
            if 0 <= ((rgb >> shift) & 0xFF) + sign * step <= 0xFF
        )
        rgb = next(c for c in candidates if c not in taken)
        colors[i] = rgb << 8 | alpha
    return colors


def _vga_hex(color: Tuple[int, int, int]) -> str:
    return '#' + ''.join(f'{(c & 0x3F) << 2:02x}' for c in color)


def _png_hex(internal_color: int) -> str:
    return f'#{internal_color >> 8:06x}'


def car_model_name(shpi_id: str) -> str:
    """CFM file name without extension, upper-cased, of an id of a resource in it"""
    file_path = shpi_id.split('__')[0].replace('\\', '/')
    return file_path.split('/')[-1].rsplit('.', 1)[0].upper()


def _palette_slice(xxx_data) -> Optional[List[str]]:
    """First PALETTE_SLICE colors of `!xxx`, None if it has fewer, holds junk (values over 63 in an 8-bit bitmap typed
    one) or black only (what the converter writes for a car without colors there)"""
    if isinstance(xxx_data.get('colors'), dict):
        colors = xxx_data['colors']['data']
        if len(colors) < PALETTE_SLICE:
            return None
        if xxx_data['resource_id'] == '24BitDos color format palette':
            result = [_png_hex(c) for c in colors[:PALETTE_SLICE]]
        else:
            # 0x24: the game shifts it to 6-bit values
            result = [_png_hex(c & 0xFCFCFCFF) for c in colors[:PALETTE_SLICE]]
    else:
        raw = xxx_data.get('bitmap')
        if not raw or len(raw) < PALETTE_SLICE * 3 or any(v > 63 for v in raw[: PALETTE_SLICE * 3]):
            return None
        result = [_vga_hex(tuple(raw[i * 3 : i * 3 + 3])) for i in range(PALETTE_SLICE)]
    return result if any(c != '#000000' for c in result) else None


def tnfs_car_colors(shpi_id: str, items: List[Tuple[str, dict, object]]) -> Dict:
    """car_colors.json of a CFM textures SHPI, the same for every car (which role a car has is up to the game: a mod
    can make any model a cop). `items` are (alias, data, block) of the SHPI children.
    - `tail_lights`: PNG color of palette index 254, the textures having it and the unlit / lit colors of the car model
      (the most common ones for a car the game has no colors of)
    - `light_bar`: PNG colors of indices 250..253, the textures having them, the cop's light bar colors and the swapped
      ones with the swap interval. The game draws them black in other cars
    - `palette_slice` (when `!xxx` holds colors): its first PALETTE_SLICE colors, the car's entries of the shared
      256-color VGA palette in 8-bit modes. Not used to draw the textures; the game reads the high-poly textures' one,
      except for the cop and the M*.CFM models (junk there)"""
    from resources.eac.bitmaps import EacImage, EacPalette

    name = car_model_name(shpi_id)
    pal_data = next((d for n, d, b in items if n == '!PAL' and isinstance(b, EacPalette)), None)
    result = {}
    if pal_data is None:
        return result
    xxx = next((d for n, d, b in items if n == '!xxx'), None)
    palette_slice = _palette_slice(xxx) if xxx else None
    if palette_slice:
        result['palette_slice'] = palette_slice

    def textures_with(indices: List[int]) -> List[str]:
        """Textures drawn with `!PAL` (an embedded palette would give other PNG colors; no CFM texture has one) that
        have any of these indices, by name"""
        return sorted(
            alias
            for alias, data, block in items
            if not alias.startswith('!')
            and isinstance(block, EacImage)
            and data['resource_id'].startswith('8Bit')
            and not data.get('embedded_palette')
            and any(i in indices for i in set(data['bitmap']))
        )

    pal_colors = car_texture_palette(pal_data['colors']['data'])
    if len(pal_colors) <= TAIL_LIGHT_INDEX:
        return result
    # an M*.CFM model has the colors of its car
    model_id = RACER_MODEL_IDS.get(name, RACER_MODEL_IDS.get(name[1:]) if name.startswith('M') else None)
    result['tail_lights'] = {
        'texture_color': _png_hex(pal_colors[TAIL_LIGHT_INDEX]),
        'textures': textures_with([TAIL_LIGHT_INDEX]),
        'off': _vga_hex(TAIL_LIGHTS_OFF.get(model_id, TAIL_LIGHTS_OFF_DEFAULT)),
        'on': _vga_hex(TAIL_LIGHTS_ON.get(model_id, TAIL_LIGHTS_ON_DEFAULT)),
    }
    result['light_bar'] = {
        'texture_colors': [_png_hex(pal_colors[i]) for i in LIGHT_BAR_INDICES],
        'textures': textures_with(LIGHT_BAR_INDICES),
        'siren_colors': [_vga_hex(c) for c in SIREN_COLORS],
        'siren_colors_swapped': [_vga_hex(c) for c in SIREN_COLORS_SWAPPED],
        'swap_interval_ms': round(SIREN_SWAP_INTERVAL_MS, 3),
    }
    return result


def _quantize_car_textures(images, num_colors: int) -> Tuple[List[List[int]], List[int]]:
    """Indices of the pixels of RGBA `PIL.Image`s (None for the ones to skip: alpha 0) on a shared palette of up to
    `num_colors` opaque colors, and that palette (0xRRGGBB). Exact when the images have no more colors (a texture set
    exported by the converter), else median cut without dithering. The same input gives the same output"""
    from PIL import Image

    pixels_per_image = [list(img.get_flattened_data()) for img in images]
    unique = {}
    for pixels in pixels_per_image:
        for r, g, b, a in pixels:
            if a:
                unique.setdefault(r << 16 | g << 8 | b, len(unique))
    if len(unique) <= num_colors:
        palette = list(unique)
        index_of = unique
    else:
        opaque = [(r, g, b) for pixels in pixels_per_image for r, g, b, a in pixels if a]
        master = Image.new('RGB', (len(opaque), 1))
        master.putdata(opaque)
        quantized = master.quantize(colors=num_colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
        rgb = quantized.getpalette('RGB')
        palette = [rgb[i] << 16 | rgb[i + 1] << 8 | rgb[i + 2] for i in range(0, len(rgb), 3)][:num_colors]
        index_of = {}
        for (r, g, b), index in zip(opaque, quantized.get_flattened_data()):
            index_of.setdefault(r << 16 | g << 8 | b, index)
    indices = [[index_of[r << 16 | g << 8 | b] if a else None for r, g, b, a in pixels] for pixels in pixels_per_image]
    return indices, palette


def deserialize_tnfs_car_textures(path: str, id: str, block) -> Dict:
    """SHPI of a CFM's textures from a directory of PNGs and its car_colors.json, as the game needs it: 8-bit textures
    on one 256-color `!PAL` (`unk1` 3: the shape height, the game adjusts width * height / 3 colors), 0..249 the colors
    of the PNGs, 250..254 the colors car_colors.json gives for them (pixels of exactly these colors get these indices),
    255 transparent (alpha 0); `!xxx` from `palette_slice` (black when missing; the game looks it up in the high-poly
    textures of every car but the cop, so the high-poly SHPI always has one)"""
    import json
    import os

    from PIL import Image

    from library.utils import path_join
    from library.utils.id import join_id
    from resources.eac.bitmaps import EacImage
    from resources.eac.utils import build_8bit_palette

    colors_path = path_join(path, 'car_colors.json')
    colors = {}
    if os.path.isfile(colors_path):
        with open(colors_path) as f:
            colors = json.load(f)
    special = {}
    if 'tail_lights' in colors:
        special[TAIL_LIGHT_INDEX] = int(colors['tail_lights']['texture_color'][1:], 16)
    if 'light_bar' in colors:
        for index, color in zip(LIGHT_BAR_INDICES, colors['light_bar']['texture_colors']):
            special[index] = int(color[1:], 16)
    index_of_special = {}
    for index, color in sorted(special.items()):
        index_of_special.setdefault(color, index)

    # "!..." files are no textures (an older export's !xxx.png)
    file_names = sorted(x for x in os.listdir(path) if x.lower().endswith('.png') and not x.startswith('!'))
    sources = [Image.open(path_join(path, file_name)).convert('RGBA') for file_name in file_names]
    images = []
    for source in sources:
        # the special colors are left out of the quantization
        image = source.copy()
        image.putdata(
            [
                (r, g, b, 0 if (r << 16 | g << 8 | b) in index_of_special else a)
                for r, g, b, a in source.get_flattened_data()
            ]
        )
        images.append(image)
    indices_per_image, palette = _quantize_car_textures(images, LIGHT_BAR_INDICES[0])

    new_shpi = block.new_data()
    new_shpi['shpi_dir'] = 'WRAP'
    palette_choice = block.item_block.get_choice_index_by_class_name('EacPalette')
    image_choice = block.item_block.get_choice_index_by_class_name('EacImage')

    def palette_item(alias, rgb_colors, palette_type):
        palette_id = join_id(id, 'children', str(len(new_shpi['children'])), 'item', 'data')
        data = build_8bit_palette([c << 8 | 0xFF for c in rgb_colors], palette_type, id=palette_id)
        data['unk1'] = b'\x03\x00'
        return {'post_offset_payload': b'', 'alias': alias, 'item': {'choice_index': palette_choice, 'data': data}}

    pal_colors = palette + [0] * (256 - len(palette))
    for index, color in special.items():
        pal_colors[index] = color
    new_shpi['children'].append(palette_item('!PAL', pal_colors, '24Bit color format palette'))
    for file_name, source, indices in zip(file_names, sources, indices_per_image):
        bitmap = []
        for (r, g, b, a), index in zip(source.get_flattened_data(), indices):
            rgb = r << 16 | g << 8 | b
            if not a:
                bitmap.append(255)
            elif rgb in index_of_special:
                bitmap.append(index_of_special[rgb])
            else:
                bitmap.append(index)
        image = EacImage().new_data()
        image['resource_id'] = '8Bit'
        image['width'] = source.width
        image['height'] = source.height
        image['bitmap'] = bitmap
        new_shpi['children'].append(
            {
                'post_offset_payload': b'',
                'alias': file_name[:-4][:4],
                'item': {'choice_index': image_choice, 'data': image},
            }
        )
    is_high_poly = id.rstrip('/').endswith('children/1/item/data')
    if 'palette_slice' in colors or is_high_poly:
        slice_colors = [int(c[1:], 16) for c in colors.get('palette_slice', [])]
        new_shpi['children'].append(
            palette_item('!xxx', slice_colors + [0] * (256 - len(slice_colors)), '24BitDos color format palette')
        )
    return new_shpi
