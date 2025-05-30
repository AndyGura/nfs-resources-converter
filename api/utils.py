"""
Utility functions for the API.
"""

from logging import warning
from typing import Dict


def apply_delta_to_resource(resource_id, resource, changes: Dict):
    """
    Apply changes to a resource.
    
    Args:
        resource_id: ID of the resource
        resource: The resource to modify
        changes: Changes to apply
    """
    suffix = '/' if '__' in resource_id else '__'
    for delta in changes:
        if not delta['id'].startswith(resource_id + suffix):
            warning('Skipped change ' + delta['id'] + '. Wrong ID')
        sub_id = delta['id'][len(resource_id) + len(suffix):]
        field = resource
        for subkey in sub_id.split('/')[:-1]:
            if isinstance(field, list):
                field = field[int(subkey)]
            else:
                field = field.get(subkey)
        if isinstance(field, list):
            field[int(sub_id.split('/')[-1])] = delta['value']
        else:
            field[sub_id.split('/')[-1]] = delta['value']