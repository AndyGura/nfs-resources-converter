import os
import tempfile
import unittest
from unittest import mock

import config


class TestConfigManagerListDefaults(unittest.TestCase):
    """
    Regression tests for the "recent_files" list-typed config option: an empty list default used
    to round-trip through the ini file as the literal string "[]", which then got split(',') into
    a bogus single-item list (['[]']) instead of staying empty.
    """

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.ini_path = os.path.join(self.temp_dir.name, 'nfs-resources-converter-settings.ini')
        self.path_patcher = mock.patch.object(config, 'CONFIG_FILE_PATH', self.ini_path)
        self.path_patcher.start()
        self.addCleanup(self.path_patcher.stop)

    def test_fresh_config_file_empty_list_default_reads_back_as_empty_list(self):
        manager = config.ConfigManager()
        manager.create_default_config_file()

        self.assertEqual(manager.get(config.SECTION_GENERAL, 'recent_files'), [])
        with open(self.ini_path) as f:
            content = f.read()
        self.assertNotIn('[]', content)

    def test_legacy_literal_brackets_in_ini_file_self_heal_to_empty_list(self):
        with open(self.ini_path, 'w') as f:
            f.write('[General]\nrecent_files = []\n')

        manager = config.ConfigManager()

        self.assertEqual(manager.get(config.SECTION_GENERAL, 'recent_files'), [])

    def test_comma_joined_recent_files_still_parses(self):
        with open(self.ini_path, 'w') as f:
            f.write('[General]\nrecent_files = a.txt,b.txt\n')

        manager = config.ConfigManager()

        self.assertEqual(manager.get(config.SECTION_GENERAL, 'recent_files'), ['a.txt', 'b.txt'])

    def test_set_then_get_round_trips_a_single_recent_file(self):
        manager = config.ConfigManager()
        manager.set(config.SECTION_GENERAL, 'recent_files', 'a.txt')

        self.assertEqual(manager.get(config.SECTION_GENERAL, 'recent_files'), ['a.txt'])


if __name__ == '__main__':
    unittest.main()
