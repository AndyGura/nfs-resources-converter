from typing import List, Dict, Any

from library import require_resource
from library.utils.id import split_last_id_part


class ChangeExecutor:

    @classmethod
    def apply_change(cls, change):
        (parent_id, id) = split_last_id_part(change['id'])
        (_, _, parent_resource), _ = require_resource(parent_id)
        if isinstance(parent_resource, list):
            resource = parent_resource[int(id)]
        else:
            resource = parent_resource[id]

        if change['op'] == 'set':
            print(f'✏️ {(parent_id + "__").split("__")[1]}/{id} = {change["newValue"]}')
            if isinstance(parent_resource, list):
                parent_resource[int(id)] = change['newValue']
            else:
                parent_resource[id] = change['newValue']
        elif change['op'] == 'array_insert':
            print(f'✏️ {(parent_id + "__").split("__")[1]}/{id} insert item at index {change["index"]}: {change["value"]}')
            resource.insert(change['index'], change['value'])
        elif change['op'] == 'array_remove':
            print(f'✏️ {(parent_id + "__").split("__")[1]}/{id} remove item at index {change["index"]}')
            del resource[change['index']]
        elif change['op'] == 'array_swap':
            print(f'✏️ {(parent_id + "__").split("__")[1]}/{id} swap indexes {change["indexA"]} and {change["indexB"]}')
            (resource[change['indexA']], resource[change['indexB']]) = (resource[change['indexB']], resource[change['indexA']])
        else:
            raise Exception(f'Unsupported operation: {change["op"]}')

    @classmethod
    def revert_change(cls, change):
        (parent_id, id) = split_last_id_part(change['id'])
        (_, _, parent_resource), _ = require_resource(parent_id)
        if isinstance(parent_resource, list):
            resource = parent_resource[int(id)]
        else:
            resource = parent_resource[id]

        if change['op'] == 'set':
            print(f'✏️ {(parent_id + "__").split("__")[1]}/{id} = {change["oldValue"]}')
            if isinstance(parent_resource, list):
                parent_resource[int(id)] = change['oldValue']
            else:
                parent_resource[id] = change['oldValue']
        elif change['op'] == 'array_insert':
            print(f'✏️ {(parent_id + "__").split("__")[1]}/{id} remove item at index {change["index"]}')
            del resource[change['index']]
        elif change['op'] == 'array_remove':
            print(f'✏️ {(parent_id + "__").split("__")[1]}/{id} insert item at index {change["index"]}: {change["oldValue"]}')
            resource.insert(change['index'], change['oldValue'])
        elif change['op'] == 'array_swap':
            print(f'✏️ {(parent_id + "__").split("__")[1]}/{id} swap indexes {change["indexA"]} and {change["indexB"]}')
            (resource[change['indexA']], resource[change['indexB']]) = (resource[change['indexB']], resource[change['indexA']])
        else:
            raise Exception(f'Unsupported operation: {change["op"]}')


class ChangesService:
    ### list of all changes that have been applied, in the order they were applied
    changes: List[Dict[str, Any]] = []
    ### an index in changes list, that is currently being applied to the data in memory
    local_revision: int = 0
    ### an index in changes list, that is currently being applied to the data on disk
    file_revision: int = 0

    ws_instance = None

    # To be called from web-socket
    @classmethod
    def on_fe_update(cls, update_dict):
        new_local_rev = update_dict['newLocalRevision']
        new_changes = update_dict['newChanges']
        popped_changes = update_dict['poppedChanges']
        if popped_changes > 0:
            new_changes_len = len(cls.changes) - popped_changes
            while new_changes_len < cls.local_revision:
                ChangeExecutor.revert_change(cls.changes[cls.local_revision - 1])
                cls.local_revision -= 1
            cls.changes = cls.changes[:-popped_changes]
        cls.changes.extend(new_changes)
        while new_local_rev < cls.local_revision:
            ChangeExecutor.revert_change(cls.changes[cls.local_revision - 1])
            cls.local_revision -= 1
        while new_local_rev > cls.local_revision:
            ChangeExecutor.apply_change(cls.changes[cls.local_revision])
            cls.local_revision += 1

    @classmethod
    def append_changes(cls, changes):
        # here we expect appended changes to be already applied to the data
        if cls.local_revision < len(cls.changes):
            cls.changes = cls.changes[:cls.local_revision]
        print(f'Appending {len(changes)} changes')
        cls.changes.extend(changes)
        cls.local_revision = len(cls.changes)
        print('new changes state:', cls.changes)
        cls.ws_instance.on_append_changes(changes)

    @classmethod
    def on_file_saved(cls):
        cls.file_revision = cls.local_revision

    @classmethod
    def clear(cls):
        print('clearing changes')
        cls.changes = []
        cls.local_revision = 0
        cls.file_revision = 0
