import unittest
from types import SimpleNamespace

from api.endpoints.checks_api import ChecksAPI
from library.changes_service import ChangesService
from library.read_blocks import DeclarativeCompoundBlock, IntegerBlock


class CheckedBlock(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        value = IntegerBlock(length=1)

    calls = 0

    def get_warnings(self, data, ctx):
        CheckedBlock.calls += 1
        return [f'value is {data["value"]}'] if data['value'] else []


class TestChecksApi(unittest.TestCase):
    def setUp(self):
        ChangesService.clear()
        CheckedBlock.calls = 0
        self.data = {'value': 0}
        file_api = SimpleNamespace(
            current_file_name='F.BIN', current_file_block=CheckedBlock(), current_file_data=self.data
        )
        self.checks_api = ChecksAPI(SimpleNamespace(file_api=file_api))

    def tearDown(self):
        ChangesService.clear()

    def _edit(self, value):
        # what ChangesService does on a GUI edit
        self.data['value'] = value
        ChangesService.changes = ChangesService.changes[: ChangesService.local_revision] + [{'op': 'set'}]
        ChangesService.local_revision = len(ChangesService.changes)

    def test_warnings_are_cached_until_the_data_changes(self):
        self.assertEqual(self.checks_api.get_warnings(), [])
        self.assertEqual(self.checks_api.get_warnings(), [])
        self.assertEqual(CheckedBlock.calls, 1)
        self._edit(1)
        self.assertEqual(self.checks_api.get_warnings(), [{'id': 'F.BIN', 'message': 'value is 1'}])
        # undo and another edit: the same revision, other data
        ChangesService.local_revision = 0
        self._edit(2)
        self.assertEqual(self.checks_api.get_warnings(), [{'id': 'F.BIN', 'message': 'value is 2'}])
        self.assertEqual(CheckedBlock.calls, 3)

    def test_compatibility(self):
        self.assertEqual(
            self.checks_api.check_compatibility('tnfs'), {'game': 'tnfs', 'state': 'unknown', 'results': []}
        )
        with self.assertRaises(ValueError):
            self.checks_api.check_compatibility('nfs99')
        # no block says which games the file is made for
        self.assertEqual(self.checks_api.get_compatibility_games(), [])
