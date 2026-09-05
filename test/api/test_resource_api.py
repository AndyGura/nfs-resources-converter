import os
import tempfile
import unittest
from unittest import mock

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


class ActionableChildBlock(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        value = IntegerBlock(length=2)

    def action_double_value(self, read_data, **kwargs):
        read_data['value'] *= 2


class OptionalActionApiTestBlock(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        marker = IntegerBlock(length=1)
        optional_field = TrailingOptionalBlock(child=ActionableChildBlock())


class NestedOptionalApiTestBlock(DeclarativeCompoundBlock):
    """
    Same shape as `OptionalActionApiTestBlock`, but with the optional field nested one level
    deeper (e.g. `a/opt_field`) - matching the GUI's `abc.fsh__a/opt_field/b` id shape, where the
    optional field sits in the middle of the path rather than at its end.
    """
    class Fields(DeclarativeCompoundBlock.Fields):
        marker = IntegerBlock(length=1)
        a = OptionalActionApiTestBlock()


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


class TestRunCustomActionOnOptionalField(unittest.TestCase):
    """
    The GUI addresses a present `OptionalBlock`/`TrailingOptionalBlock` field by the field's own
    id (there's no extra "data" path segment to step through, unlike `DelegateBlock`), so
    `require_resource` must resolve such an id straight to the child block - the one that
    actually owns the custom `action_*` methods the GUI invokes - not to the optional wrapper.
    """

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_file_path = os.path.join(self.temp_dir.name, 'test.bin')
        self.file_api = FileAPI(api=None)
        self.resource_api = ResourceAPI(api=None)

        self.original_probe_block_class = library.loader.probe_block_class

        def patched_probe_block_class(binary_file, file_path=None, length=None, resources_to_pick=None):
            if file_path and file_path.endswith('test.bin'):
                return OptionalActionApiTestBlock
            return self.original_probe_block_class(binary_file, file_path, length, resources_to_pick)

        library.loader.probe_block_class = patched_probe_block_class
        library.probe_block_class = patched_probe_block_class

        # append_changes() (invoked by a non-pure action) notifies the GUI's websocket instance;
        # there isn't one in this test process, so stub it out.
        self.original_ws_instance = ChangesService.ws_instance
        ChangesService.ws_instance = mock.Mock()

    def tearDown(self):
        library.loader.probe_block_class = self.original_probe_block_class
        library.probe_block_class = self.original_probe_block_class
        ChangesService.ws_instance = self.original_ws_instance
        ChangesService.clear()
        clear_file_cache(self.test_file_path)
        self.temp_dir.cleanup()

    def _write_and_open(self, data: bytes):
        with open(self.test_file_path, 'wb') as f:
            f.write(data)
        return self.file_api.open_file(self.test_file_path, update_recent_files=False)

    def test_run_custom_action_on_present_trailing_optional_field_delegates_to_child(self):
        # marker byte + child's 2-byte little-endian value (5), so the optional field is present
        open_res = self._write_and_open(bytes([0x01, 0x05, 0x00]))
        resource_id = f"{open_res['name']}__optional_field"

        self.resource_api.run_custom_action(resource_id, {'method': 'double_value'}, {})

        (_, _, data), _ = library.require_resource(resource_id)
        self.assertEqual(data['value'], 10)


class TestRunCustomActionOnNestedOptionalField(unittest.TestCase):
    """
    An optional field doesn't have to be the last path segment of an id - e.g. the frontend may
    request `abc.fsh__a/opt_field/b`, where `opt_field` sits in the middle of the path.
    `require_resource` must resolve the child at every step it steps through an
    `OptionalBlock`/`TrailingOptionalBlock`, not only when such a field is the final segment.
    """

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_file_path = os.path.join(self.temp_dir.name, 'test.bin')
        self.file_api = FileAPI(api=None)
        self.resource_api = ResourceAPI(api=None)

        self.original_probe_block_class = library.loader.probe_block_class

        def patched_probe_block_class(binary_file, file_path=None, length=None, resources_to_pick=None):
            if file_path and file_path.endswith('test.bin'):
                return NestedOptionalApiTestBlock
            return self.original_probe_block_class(binary_file, file_path, length, resources_to_pick)

        library.loader.probe_block_class = patched_probe_block_class
        library.probe_block_class = patched_probe_block_class

        self.original_ws_instance = ChangesService.ws_instance
        ChangesService.ws_instance = mock.Mock()

    def tearDown(self):
        library.loader.probe_block_class = self.original_probe_block_class
        library.probe_block_class = self.original_probe_block_class
        ChangesService.ws_instance = self.original_ws_instance
        ChangesService.clear()
        clear_file_cache(self.test_file_path)
        self.temp_dir.cleanup()

    def _write_and_open(self, data: bytes):
        with open(self.test_file_path, 'wb') as f:
            f.write(data)
        return self.file_api.open_file(self.test_file_path, update_recent_files=False)

    def test_field_nested_under_a_present_optional_field_is_found(self):
        # outer marker + inner marker + child's 2-byte little-endian value (5)
        open_res = self._write_and_open(bytes([0x01, 0x01, 0x05, 0x00]))
        resource_id = f"{open_res['name']}__a/optional_field/value"

        (_, res_block, res), _ = library.require_resource(resource_id)

        self.assertIsInstance(res_block, IntegerBlock)
        self.assertEqual(res, 5)

    def test_run_custom_action_on_present_optional_field_nested_mid_path_delegates_to_child(self):
        open_res = self._write_and_open(bytes([0x01, 0x01, 0x05, 0x00]))
        resource_id = f"{open_res['name']}__a/optional_field"

        self.resource_api.run_custom_action(resource_id, {'method': 'double_value'}, {})

        (_, _, data), _ = library.require_resource(resource_id)
        self.assertEqual(data['value'], 10)
