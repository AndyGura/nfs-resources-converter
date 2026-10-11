import os
import tempfile
import unittest

import numpy as np
from PIL import Image

from library.utils.nfs1_panorama_to_spherical import (
    OUT_HEIGHT,
    OUT_WIDTH,
    SE_HORIZON_SETTINGS,
    HorizonSettings,
    horizon_settings,
    nfs1_panorama_to_spherical,
)

# SIMDATA/MISC/TR2INFO of TNFS SE: ring type 0, but the mirror flag (last value) forces the ring
TR2_INFO = """#vert offset near\r\n0\r\n\r\n#vert offset far\r\n0\r\n\r\n#zoffset near\r\n0\r\n\r\n#zoffset far\r\n0\r\n
#height near\r\n0\r\n#height far\r\n48\r\n#radius near\r\n0\r\n#radius far\r\n96\r\n#colour top\r\n0 1 2\r\n
#colour bottom\r\n3 4 5\r\n#ring type? (1 is TRUE, 0 is FALSE)\r\n0\r\n
#ring y offset (bigger places horizon further down)\r\n-75\r\n#ring height\r\n112\r\n#RGB TIME OF DAY VALUES\r\n
392\r\n276\r\n190\r\n-9000\r\n206\r\n\r\n255\r\n255\r\n255\r\n0\r\n255\r\n\r\n460\r\n224\r\n144\r\n-9002\r\n203\r\n
\r\n1\r\n"""


class TestHorizonSettings(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.simdata = self.tmp.name
        os.makedirs(os.path.join(self.simdata, 'MISC'))
        with open(os.path.join(self.simdata, 'MISC', 'TR2INFO'), 'w', newline='') as f:
            f.write(TR2_INFO)

    def tearDown(self):
        self.tmp.cleanup()

    def test_other_time_of_day_reads_info_file(self):
        settings = horizon_settings(os.path.join(self.simdata, 'NTRACKFM', 'TR2_T01.FAM'))
        self.assertEqual(settings, HorizonSettings(is_ring=True, ring_y_offset=-75, ring_height=112, mirror=True))

    def test_default_time_of_day_uses_executable_table(self):
        settings = horizon_settings(os.path.join(self.simdata, 'ETRACKFM', 'TR2_001.FAM'))
        self.assertEqual(settings, SE_HORIZON_SETTINGS['tr2'])

    def test_missing_info_file_falls_back_to_executable_table(self):
        settings = horizon_settings(os.path.join(self.simdata, 'NTRACKFM', 'TR6_T01.FAM'))
        self.assertEqual(settings, SE_HORIZON_SETTINGS['tr6'])


class TestPanoramaToSpherical(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.horz = os.path.join(self.tmp.name, 'horz.png')
        self.out = os.path.join(self.tmp.name, 'spherical.png')

    def tearDown(self):
        self.tmp.cleanup()

    def _render(self, fam_name, bitmap, pivot_y=0):
        Image.fromarray(bitmap, 'RGBA').save(self.horz)
        nfs1_panorama_to_spherical(os.path.join(self.tmp.name, fam_name), self.horz, self.out, pivot_y)
        return np.asarray(Image.open(self.out))

    def test_scrolling_bitmap_puts_pivot_row_on_eye_level(self):
        bitmap = np.zeros((100, 640, 4), dtype=np.uint8)
        bitmap[..., 3] = 255
        bitmap[:60, :, 2] = 255  # blue above row 60, black from it
        out = self._render('CL1_001.FAM', bitmap, pivot_y=60)
        self.assertEqual(out.shape, (OUT_HEIGHT, OUT_WIDTH, 4))
        self.assertEqual(out[0, 0, 2], 255)
        self.assertEqual(out[OUT_HEIGHT // 2 - 3, 0, 2], 255)
        self.assertEqual(out[OUT_HEIGHT // 2 + 3, 0, 2], 0)

    def test_ring_mirrors_second_half(self):
        bitmap = np.zeros((50, 640, 4), dtype=np.uint8)
        bitmap[..., 3] = 255
        bitmap[:, :320, 0] = 255  # red left half, black right half
        out = self._render('TR3_001.FAM', bitmap)  # TR3: ring with the mirror flag
        row = out[OUT_HEIGHT // 2]
        # heading 0 at the image centre: the bitmap's left edge on both sides of it
        self.assertEqual(row[OUT_WIDTH // 2 + 10, 0], 255)
        self.assertEqual(row[OUT_WIDTH // 2 - 10, 0], 255)
        self.assertEqual(row[OUT_WIDTH // 2 + 700, 0], 0)
        self.assertEqual(row[OUT_WIDTH // 2 - 700, 0], 0)
