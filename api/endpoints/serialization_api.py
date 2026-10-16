"""
Serialization API endpoint for TailsLab.
This module handles all serialization-related operations.
"""

import copy
import time
from typing import List, Any

from library import require_resource
from library.changes_service import ChangesService
from library.utils import path_join
from library.utils.file_utils import remove_file_or_directory
from serializers import get_serializer
from serializers.misc.json_utils import convert_bytes, serialize_exceptions


class SerializationAPI:
    """
    API endpoint for serialization-related operations.
    """

    def __init__(self, api):
        """
        Initialize the SerializationAPI endpoint.

        Args:
            api: The main API instance
        """
        self.api = api

    def render_data(self, data):
        """
        Render data for frontend consumption.

        Args:
            data: The data to render

        Returns:
            Rendered data
        """
        return convert_bytes(serialize_exceptions(data))

    def serialize_resource(self, id: str, path=None, settings_patch=None) -> List[str]:
        """
        Serialize a resource.

        Args:
            id: ID of the resource
            path: Path to save the serialized resource
            changes: Changes to apply
            settings_patch: Settings to patch

        Returns:
            List of exported file paths
        """
        if settings_patch is None:
            settings_patch = {}
        (_, res_block, res), (_, top_level_block, top_level_res) = require_resource(id)
        serializer = get_serializer(res_block, res)
        static_tmp_dir = False
        if path is None:
            path = path_join(self.api.static_path, 'resources', *id.split('/'))
            static_tmp_dir = True
        path = path.replace('\\', '/')
        if settings_patch:
            serializer.patch_settings(settings_patch)
        exported_file_paths = serializer.serialize(res, path, id, res_block) or []
        exported_file_paths = [x.replace('\\', '/') for x in exported_file_paths]
        if static_tmp_dir:
            exported_file_paths = [x[len(self.api.static_path) :] for x in exported_file_paths]
        return exported_file_paths

    def new_images_from_files(self, id: str, file_paths: List[str]) -> dict:
        """
        New entries of the archive `id` holding the image files as 32-bit images, for the GUI to add to it. The
        archive is not changed here.

        Args:
            id: ID of an archive whose entries can be images (SHPI)
            file_paths: Image files (anything PIL reads)

        Returns:
            {'items': [new entry data], 'skipped': [[file name, reason]]} for the files which are not images
        """
        import os
        from PIL import UnidentifiedImageError
        from library.read_blocks import UTF8Block
        from library.read_blocks.archives import ArchiveBlock
        from resources.eac.bitmaps import EacImage
        from serializers.archives import entry_alias
        from serializers.bitmaps import ImageSerializer

        (_, archive_block, _), _ = require_resource(id)
        if not isinstance(archive_block, ArchiveBlock):
            raise Exception(f'{id} is not an archive')
        image_choice = next(
            (
                i
                for i, b in enumerate(getattr(archive_block.item_block, 'possible_blocks', []))
                if isinstance(b, EacImage)
            ),
            None,
        )
        if image_choice is None:
            raise Exception('This archive cannot hold images')
        image_block = archive_block.item_block.possible_blocks[image_choice]
        entry_block = archive_block.field_blocks_map['children'].child
        alias_block = entry_block.field_blocks_map.get('alias')
        alias_length = alias_block._get_static_length() if isinstance(alias_block, UTF8Block) else None
        items, skipped = [], []
        for path in file_paths:
            file_name = os.path.basename(path)
            try:
                image = ImageSerializer.new_image_data(path, image_block)
            except (UnidentifiedImageError, OSError) as ex:
                skipped.append([file_name, 'not an image' if isinstance(ex, UnidentifiedImageError) else str(ex)])
                continue
            entry = entry_block.new_data()
            entry['item'] = {'choice_index': image_choice, 'data': image}
            if alias_block is not None:
                entry['alias'] = entry_alias(file_name, alias_length)
            items.append(entry)
        return {'items': [self.render_data(x) for x in items], 'skipped': skipped}

    def deserialize_resource(self, id: str, file_paths: List[str], extra_opts=None) -> Any:
        """
        Deserialize a resource.

        Args:
            id: ID of the resource
            file_paths: List of file paths to use when deserializing
            extra_opts: Additional options for deserialization

        Returns:
            {'report': what the import did, for the user, or None}
        """
        (id, res_block, resource), _ = require_resource(id)
        serializer = get_serializer(res_block, resource)
        updated_data = serializer.deserialize(file_paths, id, res_block, **(extra_opts or {}))
        # other resources the import changed too (the textures of a model), applied in the same undoable change
        related = getattr(serializer, 'deserialize_related', None) or {}
        changes = self._apply_deserialized(id, resource, updated_data)
        for related_id, related_data in related.items():
            (related_id, _, related_resource), _ = require_resource(related_id)
            changes += self._apply_deserialized(related_id, related_resource, related_data)
        if changes:
            ChangesService.append_changes(
                [
                    {
                        'id': '',
                        'timestamp': int(time.time() * 1000),
                        'op': 'bundle',
                        'changes': changes,
                    }
                ]
            )
        for changed_id in [id, *related]:
            remove_file_or_directory(path_join(self.api.static_path, 'resources', *changed_id.split('/')))
        return {'report': getattr(serializer, 'deserialize_report', None)}

    def _apply_deserialized(self, id: str, resource: Any, updated_data: Any) -> list:
        """Puts the deserialized data in place of the resource loaded under `id` (a dict is updated in place), returns
        the changes for the changes model and the frontend"""
        # Snapshot the data before applying the deserialized result, so we can diff it
        # afterwards and record the mutations as changes (same approach as run_custom_action).
        if isinstance(resource, bytes):
            # bytes cannot be updated in place: the parent holds them, the change carries them
            before = resource
            resource = updated_data
        else:
            before = copy.deepcopy(resource)
            resource.clear()
            resource.update(updated_data)
        return self.api.resource_api._diff_to_changes(id, before, resource)
