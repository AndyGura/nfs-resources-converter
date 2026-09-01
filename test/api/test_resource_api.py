import os
import tempfile
import unittest

import library
import library.loader
from api.endpoints.file_api import FileAPI
from api.endpoints.resource_api import ResourceAPI
from library.changes_service import ChangesService
from library.loader import clear_file_cache
from library.read_blocks import DeclarativeCompoundBlock, IntegerBlock, TrailingOptionalBlock


class TrailingOptionalApiTestBlock(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        marker = IntegerBlock(length=1)
        trailing_field = TrailingOptionalBlock(child=IntegerBlock(length=2))


class TestGetTrailingOptionalFieldData(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_file_path = os.path.join(self.temp_dir.name, 'test.bin')
        self.file_api = FileAPI(api=None)
        self.resource_api = ResourceAPI(api=None)

        self.original_probe_block_class = library.loader.probe_block_class

        def patched_probe_block_class(binary_file, file_path=None, length=None, resources_to_pick=None):
            if file_path and file_path.endswith('test.bin'):
                return TrailingOptionalApiTestBlock
            return self.original_probe_block_class(binary_file, file_path, length, resources_to_pick)

        library.loader.probe_block_class = patched_probe_block_class
        library.probe_block_class = patched_probe_block_class

    def tearDown(self):
        library.loader.probe_block_class = self.original_probe_block_class
        library.probe_block_class = self.original_probe_block_class
        ChangesService.clear()
        clear_file_cache(self.test_file_path)
        self.temp_dir.cleanup()

    def _write_and_open(self, data: bytes):
        with open(self.test_file_path, 'wb') as f:
            f.write(data)
        return self.file_api.open_file(self.test_file_path, update_recent_files=False)

    def test_returns_new_child_data_for_absent_trailing_optional_field(self):
        open_res = self._write_and_open(bytes([0xFF]))  # no trailing data present
        self.assertIsNone(open_res['data']['trailing_field'])
        result = self.resource_api.get_trailing_optional_field_data(f"{open_res['name']}__trailing_field")
        self.assertEqual(result, 0)  # IntegerBlock.new_data() default

    def test_returns_none_for_a_non_optional_field(self):
        open_res = self._write_and_open(bytes([0xFF]))
        result = self.resource_api.get_trailing_optional_field_data(f"{open_res['name']}__marker")
        self.assertIsNone(result)
