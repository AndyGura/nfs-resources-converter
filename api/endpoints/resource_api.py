"""
Resource API endpoint for the NFS Resources Converter.
This module handles all resource-related operations.
"""

import copy
import time
from typing import Dict, Any, List

from library import require_resource
from library.changes_service import ChangesService
from library.read_blocks.optional import OptionalBlock
from library.utils.id import join_id
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

    def run_custom_action(self, resource_id: str, action: Dict, args: Dict):
        """
        Run a custom action on a resource.
        
        Args:
            resource_id: ID of the resource
            action: Action to run
            args: Arguments for the action
            
        Returns:
            Result of the action
        """
        (name, res_block, read_data), _ = require_resource(resource_id)
        action_func = getattr(res_block, f'action_{action["method"]}')

        if action.get('is_pure', False):
            action_func(name=name, read_data=read_data, **args)
            return

        # Snapshot the data before the action runs, so we can diff it afterwards and record
        # the mutations as changes in the changes model and notify the frontend.
        before = copy.deepcopy(read_data)
        action_func(name=name, read_data=read_data, **args)
        changes = self._diff_to_changes(resource_id, before, read_data)
        if changes:
            # the action already applied the mutations to read_data in place
            ChangesService.append_changes([{
                'id': '',
                'timestamp': int(time.time() * 1000),
                'op': 'bundle',
                'changes': changes,
            }])

    def _diff_to_changes(self, base_id: str, old: Any, new: Any) -> List[Dict[str, Any]]:
        """
        Recursively diff two data trees and produce a list of 'set' change entries.
        Ids are built with join_id so they match the ones the frontend generates.
        """
        timestamp = int(time.time() * 1000)
        changes: List[Dict[str, Any]] = []

        def walk(cur_id: str, o: Any, n: Any):
            if o == n:
                return
            if isinstance(o, dict) and isinstance(n, dict):
                for key in n:
                    walk(join_id(cur_id, str(key)), o.get(key), n[key])
            elif isinstance(o, list) and isinstance(n, list) and len(o) == len(n):
                if len(n) > 0 and isinstance(n[0], (str, int, float, bool, type(None))):
                    too_different = False
                    changed_items = 0
                    for (oi, ni) in enumerate(zip(o, n)):
                        if oi != ni:
                            changed_items += 1
                            if changed_items >= len(n) * 0.33:
                                too_different = True
                                break
                    if too_different:
                        changes.append({
                            'id': cur_id,
                            'timestamp': timestamp,
                            'op': 'set',
                            'oldValue': o,
                            'newValue': n,
                        })
                        return
                for i, (oi, ni) in enumerate(zip(o, n)):
                    walk(join_id(cur_id, str(i)), oi, ni)
            else:
                changes.append({
                    'id': cur_id,
                    'timestamp': timestamp,
                    'op': 'set',
                    'oldValue': o,
                    'newValue': n,
                })

        walk(base_id, old, new)
        return changes

    # FIXME this function looks strange. Can we make ut get_new_data and provie id with "/0" suffix for array,
    # and do not look intho block child attribute?
    def get_new_item_data(self, resource_id: str) -> Any:
        """
        Get new item data for a resource.
        
        Args:
            resource_id: ID of the resource
            
        Returns:
            The new item data
        """
        (_, res_block, _) = require_resource(resource_id)[0]
        if isinstance(res_block, OptionalBlock):
            res_block = res_block.child
        if hasattr(res_block, 'child'):
            return self.render_data(res_block.child.new_data())
        return None
