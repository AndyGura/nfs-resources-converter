import os
import tempfile
import unittest

import library
import library.loader
from api.endpoints.changes_api import ChangesAPI
from api.endpoints.file_api import FileAPI
from library.changes_service import ChangesService
from library.loader import clear_file_cache
from library.read_blocks import DeclarativeCompoundBlock, UTF8Block


class TestText(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        text = UTF8Block(length=lambda ctx: ctx.read_bytes_remaining)


class TestFrontendChangesWorkflow(unittest.TestCase):

    def setUp(self):
        # Create a temporary directory and a test.txt file inside it
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_file_path = os.path.join(self.temp_dir.name, 'test.txt')
        
        # Write initial content to the text file
        with open(self.test_file_path, 'w', encoding='utf-8') as f:
            f.write("Initial Content")
            
        # Instantiate APIs
        self.file_api = FileAPI(api=None)
        self.changes_api = ChangesAPI(api=None)

        # Monkey-patch probe_block_class to support TestText temporarily for tests
        self.original_probe_block_class = library.loader.probe_block_class

        def patched_probe_block_class(binary_file, file_path=None, resources_to_pick=None):
            if file_path and file_path.endswith('test.txt'):
                return TestText
            return self.original_probe_block_class(binary_file, file_path, resources_to_pick)

        library.loader.probe_block_class = patched_probe_block_class
        library.probe_block_class = patched_probe_block_class

    def tearDown(self):
        # Restore the original probe_block_class
        library.loader.probe_block_class = self.original_probe_block_class
        library.probe_block_class = self.original_probe_block_class

        # Clean up cache and ChangesService state
        ChangesService.clear()
        clear_file_cache(self.test_file_path)
        self.temp_dir.cleanup()

    def test_frontend_changes_save_workflow(self):
        # 1. Open the file
        open_res = self.file_api.open_file(self.test_file_path, update_recent_files=False)
        self.assertEqual(open_res['data']['text'], "Initial Content")
        self.assertIsInstance(self.file_api.current_file_block, TestText)

        # 2. Emit first change as frontend
        change1 = {
            'id': f"{open_res['name']}__text",
            'op': 'set',
            'newValue': 'First Change'
        }
        update_dict1 = {
            'newLocalRevision': 1,
            'newChanges': [change1],
            'poppedChanges': 0
        }
        self.changes_api.on_fe_update(update_dict1)
        
        # Assert the local in-memory data got updated
        self.assertEqual(self.file_api.current_file_data['text'], 'First Change')
        self.assertEqual(ChangesService.local_revision, 1)

        # 3. Save the file and assert file is correctly updated on disk
        self.file_api.save_file(self.test_file_path)
        with open(self.test_file_path, 'r', encoding='utf-8') as f:
            saved_content1 = f.read()
        self.assertEqual(saved_content1, 'First Change')

        # 4. Emit second change as frontend
        change2 = {
            'id': f"{open_res['name']}__text",
            'op': 'set',
            'newValue': 'Second Change'
        }
        update_dict2 = {
            'newLocalRevision': 2,
            'newChanges': [change2],
            'poppedChanges': 0
        }
        self.changes_api.on_fe_update(update_dict2)

        # Assert the local in-memory data got updated
        self.assertEqual(self.file_api.current_file_data['text'], 'Second Change')
        self.assertEqual(ChangesService.local_revision, 2)

        # 5. Save the file again and assert file is correctly updated on disk again
        self.file_api.save_file(self.test_file_path)
        with open(self.test_file_path, 'r', encoding='utf-8') as f:
            saved_content2 = f.read()
        self.assertEqual(saved_content2, 'Second Change')
