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

    def serialize_resource(self, id: str, settings_patch: Dict = {}) -> List[str]:
        """
        Serialize a resource.
        
        Args:
            id: ID of the resource
            settings_patch: Settings to patch
            
        Returns:
            List of exported file paths
        """
        (_, res_block, res), (_, top_level_block, top_level_res) = require_resource(id)
        serializer = get_serializer(res_block, res)
        path = path_join(self.api.static_path, 'resources', *id.split('/'))
        if settings_patch:
            serializer.patch_settings(settings_patch)
        serializer.serialize(res, path, id, res_block)
        normal_slashes_path = path.replace('\\', '/')
        exported_file_paths = [str(x)[len(self.api.static_path):]
                               for x in chain(Path(normal_slashes_path).glob("**/*"),
                                              Path(normal_slashes_path[:normal_slashes_path.rindex('/')]).glob(
                                                  normal_slashes_path[
                                                  (normal_slashes_path.rindex('/') + 1):] + '.*'))
                               if not x.is_dir()]
        return [x.replace('\\', '/') for x in exported_file_paths]

    def serialize_reversible(self, id: str, changes: Dict) -> Tuple[List[str], bool]:
        """
        Serialize a resource with ability to serialize it back.
        
        Args:
            id: ID of the resource
            changes: Changes to apply
            
        Returns:
            Tuple of (file list, flag indicating if it's possible to deserialize files back)
        """
        (id, res_block, resource), _ = require_resource(id)
        resource = deepcopy(resource)
        apply_delta_to_resource(id, resource, changes)
        serializer = get_serializer(res_block, resource)
        path = path_join(self.api.static_path, 'resources_edit', *id.split('/'))
        reverse_flag = serializer.setup_for_reversible_serialization()
        serializer.serialize(resource, path, id, res_block)
        normal_slashes_path = path.replace('\\', '/')
        return [str(x)[len(self.api.static_path):]
                for x in chain(Path(normal_slashes_path).glob("**/*"),
                               Path(normal_slashes_path[:normal_slashes_path.rindex('/')]).glob(
                                   normal_slashes_path[(normal_slashes_path.rindex('/') + 1):] + '.*'))
                if not x.is_dir()], reverse_flag

    def serialize_resource_tmp(self, id: str, changes: Dict, settings_patch: Dict = {}) -> List[str]:
        """
        Serialize a resource temporarily.
        
        Args:
            id: ID of the resource
            changes: Changes to apply
            settings_patch: Settings to patch
            
        Returns:
            List of exported file paths
        """
        (_, res_block, resource), _ = require_resource(id)
        resource = deepcopy(resource)
        apply_delta_to_resource(id, resource, changes)
        serializer = get_serializer(res_block, resource)
        path = path_join(self.api.static_path, 'resources_tmp', *id.split('/'))
        if settings_patch:
            serializer.patch_settings(settings_patch)
        serializer.serialize(resource, path, id, res_block)
        normal_slashes_path = path.replace('\\', '/')
        return [str(x)[len(self.api.static_path):]
                for x in chain(Path(normal_slashes_path).glob("**/*"),
                               Path(normal_slashes_path[:normal_slashes_path.rindex('/')]).glob(
                                   normal_slashes_path[(normal_slashes_path.rindex('/') + 1):] + '.*'))
                if not x.is_dir()]

    def deserialize_resource(self, id: str) -> Any:
        """
        Deserialize a resource.
        
        Args:
            id: ID of the resource
            
        Returns:
            The deserialized resource
        """
        (id, res_block, resource), _ = require_resource(id)
        serializer = get_serializer(res_block, resource)
        path = path_join(self.api.static_path, 'resources_edit', *id.split('/'))
        updated_data = serializer.deserialize(path, id, res_block)
        resource.clear()
        resource.update(updated_data)
        remove_file_or_directory(path_join(self.api.static_path, 'resources', *id.split('/')))
        remove_file_or_directory(path_join(self.api.static_path, 'resources_tmp', *id.split('/')))
        remove_file_or_directory(path_join(self.api.static_path, 'resources_edit', *id.split('/')))
        return self.render_data(resource)
