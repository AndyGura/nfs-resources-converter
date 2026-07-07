from api.bridge import bridge

from library.changes_service import ChangesService
from serializers.misc.json_utils import revert_bytes, convert_bytes


class ChangesAPI:
    def __init__(self, api):
        self.api = api
        ChangesService.ws_instance = bridge

    def get_revisions(self):
        return (ChangesService.file_revision, ChangesService.local_revision)

    def get_changes(self):
        return convert_bytes(ChangesService.changes)

    def on_fe_update(self, update_dict):
        update_dict = revert_bytes(update_dict)
        ChangesService.on_fe_update(update_dict)
