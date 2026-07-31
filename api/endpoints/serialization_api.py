"""
Serialization API endpoint for the NFS Resources Converter.
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
            exported_file_paths = [x[len(self.api.static_path):] for x in exported_file_paths]
        return exported_file_paths

    def deserialize_resource(self, id: str, file_paths : List[str], extra_opts=None) -> Any:
        """
        Deserialize a resource.
        
        Args:
            id: ID of the resource
            file_paths: List of file paths to use when deserializing
            extra_opts: Additional options for deserialization
            
        Returns:
            The deserialized resource
        """
        (id, res_block, resource), _ = require_resource(id)
        serializer = get_serializer(res_block, resource)
        updated_data = serializer.deserialize(file_paths, id, res_block, **(extra_opts or {}))
        # Snapshot the data before applying the deserialized result, so we can diff it
        # afterwards and record the mutations as changes in the changes model and notify
        # the frontend (same approach as run_custom_action).
        if isinstance(resource, bytes):
            before = resource
            resource = updated_data
        else:
            before = copy.deepcopy(resource)
            resource.clear()
            resource.update(updated_data)
        changes = self.api.resource_api._diff_to_changes(id, before, resource)
        if changes:
            # the mutations have already been applied to resource in place
            ChangesService.append_changes([{
                'id': '',
                'timestamp': int(time.time() * 1000),
                'op': 'bundle',
                'changes': changes,
            }])
        remove_file_or_directory(path_join(self.api.static_path, 'resources', *id.split('/')))
        return self.render_data(resource)
