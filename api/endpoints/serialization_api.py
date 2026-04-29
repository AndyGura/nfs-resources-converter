"""
Serialization API endpoint for the NFS Resources Converter.
This module handles all serialization-related operations.
"""

from copy import deepcopy
from itertools import chain
from pathlib import Path
from typing import Dict, List, Tuple, Any

from api.utils import apply_delta_to_resource
from library import require_resource
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

    def serialize_resource(self, id: str, path=None, changes=None, settings_patch=None) -> List[str]:
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
        if changes:
            res = deepcopy(res)
            apply_delta_to_resource(id, res, changes)
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
        resource.clear()
        resource.update(updated_data)
        remove_file_or_directory(path_join(self.api.static_path, 'resources', *id.split('/')))
        return self.render_data(resource)
