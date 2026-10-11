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


class TestConversionPresets(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.ini_path = os.path.join(self.temp_dir.name, 'nfs-resources-converter-settings.ini')
        # a settings file of a version without presets
        with open(self.ini_path, 'w') as f:
            f.write(
                '[Conversion]\n'
                'input_path = /in\n'
                'output_path = /out\n'
                'images__save_mipmaps = True\n'
                'maps__add_props_to_obj = False\n'
                'multiprocess_processes_count = 3\n'
            )
        for patcher in (
            mock.patch.object(config, 'CONFIG_FILE_PATH', self.ini_path),
            mock.patch.object(config, '_config_manager', None),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        config._config_manager = config.ConfigManager()

    def test_conversion_section_without_presets_is_no_preset(self):
        self.assertEqual(config.list_conversion_presets(), [])
        self.assertIsNone(config.get_selected_conversion_preset())
        settings = config.conversion_config()
        self.assertEqual(settings.input_path, '/in')
        self.assertTrue(settings.images__save_mipmaps)
        self.assertFalse(settings.maps__add_props_to_obj)
        self.assertEqual(settings.multiprocess_processes_count, 3)

    def test_created_preset_copies_settings_and_is_edited_separately(self):
        config.create_conversion_preset('My Preset')
        config.patch_conversion_preset_settings(
            {'images__save_mipmaps': False, 'input_path': '/other_in'}, preset='My Preset'
        )

        self.assertEqual(config.list_conversion_presets(), ['My Preset'])
        preset = config.conversion_config(preset='My Preset')
        self.assertFalse(preset.images__save_mipmaps)
        self.assertFalse(preset.maps__add_props_to_obj)
        self.assertEqual(preset.multiprocess_processes_count, 3)
        self.assertEqual(preset.input_path, '/other_in')
        self.assertEqual(preset.output_path, '/out')
        no_preset = config.conversion_config()
        self.assertTrue(no_preset.images__save_mipmaps)
        self.assertEqual(no_preset.input_path, '/in')
        with open(self.ini_path) as f:
            content = f.read()
        self.assertIn('[Conversion: My Preset]', content)
        self.assertNotIn('selected_preset', content.split('[Conversion: My Preset]')[1])

    def test_preset_without_a_setting_takes_the_built_in_default(self):
        with open(self.ini_path, 'a') as f:
            f.write('[Conversion: old]\nimages__save_mipmaps = True\n')
        config._config_manager = config.ConfigManager()

        preset = config.conversion_preset_settings('old')

        self.assertTrue(preset['images__save_mipmaps'])
        self.assertTrue(preset['maps__add_props_to_obj'])
        self.assertEqual(preset['multiprocess_processes_count'], 0)
        self.assertEqual(preset['input_path'], '')
        self.assertNotIn('selected_preset', preset)

    def test_copy_from_another_preset(self):
        config.create_conversion_preset('a')
        config.patch_conversion_preset_settings({'geometry__save_blend': False}, preset='a')
        config.create_conversion_preset('b', copy_from='a')

        self.assertFalse(config.conversion_preset_settings('b')['geometry__save_blend'])
        self.assertTrue(config.conversion_preset_settings()['geometry__save_blend'])

    def test_selected_preset(self):
        config.create_conversion_preset('nfs-web-assets')
        config.set_selected_conversion_preset('nfs-web-assets')
        self.assertEqual(config.get_selected_conversion_preset(), 'nfs-web-assets')

        config.delete_conversion_preset('nfs-web-assets')

        self.assertEqual(config.list_conversion_presets(), [])
        self.assertIsNone(config.get_selected_conversion_preset())
        self.assertEqual(config.get_config(config.SECTION_CONVERSION, 'selected_preset'), '')

    def test_unknown_preset_raises(self):
        for func in (
            lambda: config.conversion_config(preset='missing'),
            lambda: config.patch_conversion_preset_settings({'images__save_mipmaps': True}, preset='missing'),
            lambda: config.delete_conversion_preset('missing'),
            lambda: config.set_selected_conversion_preset('missing'),
            lambda: config.patch_conversion_preset_settings({'selected_preset': 'x'}),
        ):
            with self.assertRaises(ValueError):
                func()
        self.assertEqual(config.list_conversion_presets(), [])

    def test_preset_names(self):
        config.create_conversion_preset('Existing')
        for name in ('My Preset', 'nfs-web-assets', 'v1.2_x', 'a', '9'):
            self.assertIsNone(config.validate_conversion_preset_name(name), name)
        for name in (
            '',
            ' lead',
            'trail ',
            'with"quote',
            "with'quote",
            'semi;colon',
            'brack]et',
            '-dash',
            'x' * 65,
            'no PRESET',
            'existing',
        ):
            self.assertIsNotNone(config.validate_conversion_preset_name(name), name)
        with self.assertRaises(ValueError):
            config.create_conversion_preset('bad"name')


if __name__ == '__main__':
    unittest.main()
