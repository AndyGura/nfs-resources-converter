import os
import tempfile
import unittest

from library.utils.file_utils import find_files_case_insensitive


class TestFindFilesCaseInsensitive(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        os.makedirs(os.path.join(self.root, 'SimData', 'ETRACKFM'))
        for rel in [
            'tr0.qfs',
            'TRN0.qFS',
            'sky.qfs',
            'Tr.frd',
            'SimData/ETRACKFM/AL1_001.FAM',
            'SimData/ETRACKFM/AL1_002.FAM',
        ]:
            open(os.path.join(self.root, rel), 'wb').close()

    def tearDown(self):
        self.tmp.cleanup()

    def test_exact_name_any_case(self):
        self.assertEqual(
            find_files_case_insensitive([os.path.join(self.root, 'Tr0.QFS')]),
            [os.path.join(self.root, 'tr0.qfs')],
        )

    def test_wildcards_and_order(self):
        found = find_files_case_insensitive(
            [os.path.join(self.root, 'Trn0.QFS'), os.path.join(self.root, '*.QFS')],
        )
        self.assertEqual(
            found,
            [os.path.join(self.root, x) for x in ['TRN0.qFS', 'sky.qfs', 'tr0.qfs']],
        )

    def test_directory_case(self):
        self.assertEqual(
            find_files_case_insensitive([os.path.join(self.root, 'SIMDATA', 'etrackfm', 'AL1_*.FAM')]),
            [os.path.join(self.root, 'SimData', 'ETRACKFM', x) for x in ['AL1_001.FAM', 'AL1_002.FAM']],
        )

    def test_missing(self):
        self.assertEqual(find_files_case_insensitive([os.path.join(self.root, 'NOPE', '*.FAM')]), [])
