import os
import shutil
import tempfile
import unittest
from unittest import mock

from api.endpoints.changes_api import ChangesAPI
from api.endpoints.file_api import FileAPI
from api.endpoints.resource_api import ResourceAPI
from library import require_file
from library.changes_service import ChangesService
from library.lazy import is_loaded
from library.loader import clear_file_cache, files_cache, path_to_name, pinned_files
from serializers.misc.json_utils import LAZY_MARKER

SAMPLE = 'test/golden_corpus/GRAPHICS.FSH'


def _has_marker(node) -> bool:
    if isinstance(node, dict):
        return node.get(LAZY_MARKER) is True or any(_has_marker(v) for v in node.values())
    if isinstance(node, list):
        return any(_has_marker(v) for v in node)
    return False


class TestLazyPartsInGui(unittest.TestCase):
    """The GUI gets unloaded archive entries as markers and asks for them one by one"""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.path = os.path.join(self.tmp_dir, 'GRAPHICS.FSH')
        shutil.copy(SAMPLE, self.path)
        self.file_api = FileAPI(api=None)
        self.resource_api = ResourceAPI(api=None)
        self.changes_api = ChangesAPI(api=None)
        self.original_ws_instance = ChangesService.ws_instance
        ChangesService.ws_instance = mock.Mock()

    def tearDown(self):
        ChangesService.ws_instance = self.original_ws_instance
        ChangesService.clear()
        clear_file_cache(self.path)
        shutil.rmtree(self.tmp_dir)

    def test_open_file_renders_unloaded_entries_as_markers(self):
        res = self.file_api.open_file(self.path, update_recent_files=False)
        child = res['data']['children'][1]
        self.assertTrue(child[LAZY_MARKER])
        self.assertIsInstance(child['alias'], str)
        self.assertNotIn('item', child)
        self.assertFalse(any(is_loaded(c) for c in self.file_api.current_file_data['children']))

    def test_load_lazy_part_parses_one_entry(self):
        res = self.file_api.open_file(self.path, update_recent_files=False)
        loaded = self.resource_api.load_lazy_part(f'{res["name"]}__children/1')
        self.assertNotIn(LAZY_MARKER, loaded)
        self.assertEqual(list(loaded.keys()), ['item', 'alias', 'post_offset_payload'])
        self.assertIn('width', loaded['item']['data'])
        children = self.file_api.current_file_data['children']
        self.assertTrue(is_loaded(children[1]))
        self.assertFalse(any(is_loaded(c) for i, c in enumerate(children) if i != 1))
        # the next render of the file shows it loaded
        rendered = self.file_api.render_data(self.file_api.current_file_data)
        self.assertNotIn(LAZY_MARKER, rendered['children'][1])
        self.assertTrue(rendered['children'][2][LAZY_MARKER])

    def test_retrieve_value_loads_everything(self):
        res = self.file_api.open_file(self.path, update_recent_files=False)
        value = self.resource_api.retrieve_value(res['name'])
        self.assertFalse(_has_marker(value))
        self.assertTrue(all(is_loaded(c) for c in self.file_api.current_file_data['children']))

    def test_change_of_unloaded_entry_and_save(self):
        res = self.file_api.open_file(self.path, update_recent_files=False)
        self.changes_api.on_fe_update(
            {
                'newLocalRevision': 1,
                'poppedChanges': 0,
                'newChanges': [
                    {
                        'id': f'{res["name"]}__children/2/alias',
                        'timestamp': 0,
                        'op': 'set',
                        'oldValue': res['data']['children'][2]['alias'],
                        'newValue': 'abcd',
                    }
                ],
            }
        )
        children = self.file_api.current_file_data['children']
        self.assertTrue(is_loaded(children[2]))
        self.assertEqual(children[2]['alias'], 'abcd')
        self.assertFalse(is_loaded(children[3]))
        saved = self.file_api.save_file(self.path)
        self.assertEqual(saved['children'][2]['alias'], 'abcd')
        # untouched entries were written as their original bytes, the saved file is read lazily again
        with open(SAMPLE, 'rb') as f:
            original = f.read()
        with open(self.path, 'rb') as f:
            written = f.read()
        self.assertEqual(len(written), len(original))
        self.assertTrue(saved['children'][3][LAZY_MARKER])


class TestFileCacheBound(unittest.TestCase):
    SAMPLES = ['test/samples/VERTBST.FSH', 'test/golden_corpus/GRAPHICS.FSH', 'test/samples/nfs3_f355.viv']

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.paths = []
        for sample in self.SAMPLES:
            path = os.path.join(self.tmp_dir, os.path.basename(sample))
            shutil.copy(sample, path)
            self.paths.append(path)
        self.file_api = FileAPI(api=None)

    def tearDown(self):
        ChangesService.clear()
        for path in self.paths:
            clear_file_cache(path)
        shutil.rmtree(self.tmp_dir)

    def test_least_recently_required_file_is_dropped_but_not_the_open_one(self):
        with mock.patch.dict(os.environ, {'NFS_RESOURCES_CONVERTER_GENERAL_FILE_CACHE_SIZE': '2'}):
            self.file_api.open_file(self.paths[0], update_recent_files=False)
            self.assertIn(path_to_name(self.paths[0]), pinned_files)
            (_, _, second) = require_file(self.paths[1])
            require_file(self.paths[2])
            cached = set(files_cache.keys())
        self.assertIn(path_to_name(self.paths[0]), cached)
        self.assertNotIn(path_to_name(self.paths[1]), cached)
        self.assertIn(path_to_name(self.paths[2]), cached)
        # the dropped tree is still usable by whoever holds it
        self.assertIn('width', second['children'][0]['item']['data'])
        # the next file open drops the previous one from the cache and pins the new one
        self.file_api.open_file(self.paths[1], update_recent_files=False)
        self.assertNotIn(path_to_name(self.paths[0]), files_cache)
        self.assertNotIn(path_to_name(self.paths[0]), pinned_files)
        self.assertIn(path_to_name(self.paths[1]), pinned_files)
        self.file_api.close_file()
        self.assertNotIn(path_to_name(self.paths[1]), pinned_files)
