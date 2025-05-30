"""
Resource API endpoint for the NFS Resources Converter.
This module handles all resource-related operations.
"""

from typing import Dict, Any

from library import require_resource
from serializers.misc.json_utils import convert_bytes, serialize_exceptions


class ResourceAPI:
    """
    API endpoint for resource-related operations.
    """
    
    def __init__(self, api):
        """
        Initialize the ResourceAPI endpoint.
        
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
    
    def retrieve_value(self, resource_id: str) -> Any:
        """
        Retrieve a value from a resource.
        
        Args:
            resource_id: ID of the resource
            
        Returns:
            The resource value
        """
        (_, _, resource), _ = require_resource(resource_id)
        return self.render_data(resource)
    
    def run_custom_action(self, resource_id: str, action: Dict, args: Dict) -> Any:
        """
        Run a custom action on a resource.
        
        Args:
            resource_id: ID of the resource
            action: Action to run
            args: Arguments for the action
            
        Returns:
            Result of the action
        """
        (name, res_block, resource), _ = require_resource(resource_id)
        action_func = getattr(res_block, f'action_{action["method"]}')
        action_func(resource, **args)
        return self.render_data(resource)