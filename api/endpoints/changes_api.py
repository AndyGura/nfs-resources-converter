import eel

from library.changes_service import ChangesService


class ChangesAPI:
    def __init__(self, api):
        self.api = api
        ChangesService.ws_instance = eel

    def get_revisions(self):
        return (ChangesService.file_revision, ChangesService.local_revision)

    def get_changes(self):
        return ChangesService.changes

    def on_fe_update(self, update_dict):
        ChangesService.on_fe_update(update_dict)
