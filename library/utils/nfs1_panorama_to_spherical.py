"""
The horizon of a TNFS track (bitmap "horz" of its FAM) on an equirectangular sky sphere texture, placed as Win95 SE
draws it.

The game has no sky sphere: before the 3D scene it paints the horz bitmap on the screen (FUN_0043af80), in one of two
ways, picked by the track's "ring type" horizon setting:
- 0, scrolling bitmap (FUN_0043ae64): a cylinder of 1280 texels per full turn around the camera (FUN_0043a028), rows
  2 px high on the 640x480 screen; the row `pivot_y` of the bitmap lies on the horizon line (eye level).
- 1, horizon ring (built by FUN_0043abfc, drawn by FUN_0043b298): 16 points around the camera at eye level, a textured
  quad between each two neighbours. The bitmap spans 8 quads (180 degrees) and repeats, mirrored in the second half
  with the mirror flag. The quads have a fixed height on the screen: texel rows 1..H-2 stretch from
  `ring_y_offset - ring_height` to `ring_y_offset + ring_height` px (640x480) below the horizon line, `pivot_y` is
  not used.
Above and below the bitmap the screen gets its first and its last pixel.

The horizon settings come from SIMDATA/MISC/<track>INFO when a time of day other than the default is selected (FAM
`<track>_T01`), otherwise (`_001`, also `_M01` of the mirrored track and `_R01` of rally mode) from a table in the
executable (FUN_0043a370). An INFO mirror flag forces the ring.

On the sphere a pixel offset y below the horizon line is the elevation -atan(y / F), F being the focal length of the SE
projection (gfx_set_fov 0x475fab: (width / 2) / tan(fov / 2) for both axes) of the 640 px wide view with the 96
degrees horizontal FOV of every camera but the in-car one (85 degrees).
"""

import math
import os
from os.path import basename, dirname, join
from typing import NamedTuple, Optional

GAME_FOCAL_PX = 320 / math.tan(math.radians(48))
# scrolling bitmap: texels per full turn, screen px per texel row (640x480)
SCROLL_TEXELS_PER_TURN = 1280
SCROLL_ROW_HEIGHT_PX = 2

OUT_WIDTH = 2048
OUT_HEIGHT = 1024


class HorizonSettings(NamedTuple):
    is_ring: bool
    ring_y_offset: int
    ring_height: int
    mirror: bool


def _settings(ring_type, ring_y_offset, ring_height, mirror) -> HorizonSettings:
    return HorizonSettings(bool(ring_type or mirror), ring_y_offset, ring_height, bool(mirror))


# Win95 SE built-in horizon settings (33 ints per track from 0x4bb094: INFO values in INFO order), the ones used here
_OPEN_ROAD = _settings(0, -50, 112, 0)
SE_HORIZON_SETTINGS = {
    'cl1': _OPEN_ROAD,
    'cl2': _OPEN_ROAD,
    'cl3': _OPEN_ROAD,
    'al1': _OPEN_ROAD,
    'al2': _OPEN_ROAD,
    'al3': _OPEN_ROAD,
    'cy1': _OPEN_ROAD,
    'cy2': _OPEN_ROAD,
    'cy3': _OPEN_ROAD,
    'tr1': _settings(1, -60, 112, 0),
    'tr2': _settings(1, -80, 112, 0),
    'tr3': _settings(1, -20, 112, 1),
    'tr4': _settings(1, -100, 112, 0),
    'tr5': _settings(1, -50, 112, 1),
    'tr6': _settings(1, -20, 112, 0),
    'tr7': _settings(1, -50, 112, 1),
}
# tracks the game has no settings for (TR8_R01.FAM)
DEFAULT_HORIZON_SETTINGS = _settings(1, -50, 112, 0)


def _atoi(text: str) -> int:
    digits = len(text) - len(text.lstrip('+-0123456789'))
    try:
        return int(text[:digits])
    except ValueError:
        return 0


def read_info_file(path: str) -> Optional[HorizonSettings]:
    """
    Horizon settings of a SIMDATA/MISC/<track>INFO text file: one value per non-comment line (colours: 3 on a line), 8
    ring geometry values, top and bottom colour, ring type, ring y offset, ring height, 15 time of day values and the
    mirror flag
    """
    with open(path, 'r', errors='replace') as f:
        values = [
            _atoi(token)
            for line in f.read().replace('\r', '\n').split('\n')
            if line.strip() and not line.strip().startswith('#')
            for token in line.split()
        ]
    if len(values) < 17:
        return None
    return _settings(values[14], values[15], values[16], values[32] if len(values) > 32 else 0)


def _find_info_file(fam_path: str, track: str) -> Optional[str]:
    misc_dir = join(dirname(dirname(fam_path)), 'MISC')
    try:
        names = os.listdir(misc_dir)
    except OSError:
        return None
    name = next((x for x in names if x.lower() == f'{track}info'), None)
    return join(misc_dir, name) if name else None


def horizon_settings(fam_path: str) -> HorizonSettings:
    name = basename(fam_path).lower()
    track = name[:3]
    if name[4:5] == 't':
        info_path = _find_info_file(fam_path, track)
        settings = read_info_file(info_path) if info_path else None
        if settings:
            return settings
    return SE_HORIZON_SETTINGS.get(track, DEFAULT_HORIZON_SETTINGS)


def _sample_rows(source, coords):
    import numpy as np

    coords = np.clip(coords - 0.5, 0, source.shape[0] - 1)
    i0 = np.floor(coords).astype(int)
    i1 = np.minimum(i0 + 1, source.shape[0] - 1)
    t = (coords - i0)[:, None, None]
    return source[i0] * (1 - t) + source[i1] * t


def _sample_columns_wrapped(source, coords):
    import numpy as np

    width = source.shape[1]
    coords = np.mod(coords - 0.5, width)
    j0 = np.floor(coords).astype(int)
    j1 = (j0 + 1) % width
    t = (coords - j0)[None, :, None]
    return source[:, j0] * (1 - t) + source[:, j1] * t


def nfs1_panorama_to_spherical(fam_path: str, file_name: str, out_file_name: str, pivot_y: int):
    import numpy as np
    from PIL import Image

    settings = horizon_settings(fam_path)
    source = np.asarray(Image.open(file_name).convert('RGBA'), dtype=np.float32)
    height, width = source.shape[:2]

    # pixels below the eye level horizon line (640x480) of the output rows, from the top (+90 deg) to the bottom
    elevation = (0.5 - (np.arange(OUT_HEIGHT) + 0.5) / OUT_HEIGHT) * math.pi
    screen_y = -GAME_FOCAL_PX * np.tan(elevation)
    if settings.is_ring:
        top = settings.ring_y_offset - settings.ring_height
        bottom = settings.ring_y_offset + settings.ring_height
        rows = 1 + (screen_y - top) / (bottom - top) * (height - 3)
    else:
        top = -pivot_y * SCROLL_ROW_HEIGHT_PX
        bottom = top + (height - 1) * SCROLL_ROW_HEIGHT_PX
        rows = (screen_y - top) / SCROLL_ROW_HEIGHT_PX

    # output columns: heading from the image centre to the right, the bitmap starts at heading 0
    heading = np.mod((np.arange(OUT_WIDTH) + 0.5) / OUT_WIDTH * 360 - 180, 360)
    if settings.is_ring:
        columns = np.mod(heading, 180) / 180 * width
        if settings.mirror:
            columns = np.where(heading >= 180, width - columns, columns)
    else:
        columns = heading / 360 * SCROLL_TEXELS_PER_TURN

    out = np.empty((OUT_HEIGHT, OUT_WIDTH, 4), dtype=np.float32)
    out[screen_y < top] = source[0, 0]
    out[screen_y >= bottom] = source[-1, -1]
    band = (screen_y >= top) & (screen_y < bottom)
    out[band] = _sample_columns_wrapped(_sample_rows(source, rows[band]), columns)
    Image.fromarray(np.round(out).astype(np.uint8), 'RGBA').save(out_file_name)
