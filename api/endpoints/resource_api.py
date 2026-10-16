"""
Resource API endpoint for the NFS Resources Converter.
This module handles all resource-related operations.
"""

import copy
import time
from typing import Dict, Any, List

from library import require_resource
from library.changes_service import ChangesService
from library.lazy import LazyDict, load_all
from library.read_blocks.optional import OptionalBlock, TrailingOptionalBlock
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
        # a whole value, for code which reads it as a tree: every lazy part inside is parsed
        return self.render_data(load_all(resource))

    def load_lazy_part(self, resource_id: str) -> Any:
        """
        Parse an unloaded lazy part (archive entry, bundle chunk) and return its rendered data. Lazy parts
        nested in it stay unloaded, rendered as markers.

        Args:
            resource_id: ID of the lazy part

        Returns:
            The rendered data of the part
        """
        (_, _, resource), _ = require_resource(resource_id)
        if isinstance(resource, LazyDict):
            resource.load()
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
            action_func(name=name, read_data=read_data, id=resource_id, **args)
            return

        # Snapshot the data before the action runs, so we can diff it afterwards and record
        # the mutations as changes in the changes model and notify the frontend.
        before = copy.deepcopy(read_data)
        action_func(name=name, read_data=read_data, id=resource_id, **args)
        changes = self._diff_to_changes(resource_id, before, read_data)
        if changes:
            # the action already applied the mutations to read_data in place
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
            elif (
                isinstance(o, list) and isinstance(n, list) and len(n) > len(o) and all(isinstance(x, dict) for x in n)
            ):
                # entries added at the end (an archive): the others are diffed one by one
                for i, (oi, ni) in enumerate(zip(o, n)):
                    walk(join_id(cur_id, str(i)), oi, ni)
                for i in range(len(o), len(n)):
                    changes.append(
                        {'id': cur_id, 'timestamp': timestamp, 'op': 'array_insert', 'index': i, 'value': n[i]}
                    )
            elif isinstance(o, list) and isinstance(n, list) and len(o) == len(n):
                if len(n) > 0 and isinstance(n[0], (str, int, float, bool, type(None))):
                    too_different = False
                    changed_items = 0
                    for oi, ni in enumerate(zip(o, n)):
                        if oi != ni:
                            changed_items += 1
                            if changed_items >= len(n) * 0.33:
                                too_different = True
                                break
                    if too_different:
                        changes.append(
                            {
                                'id': cur_id,
                                'timestamp': timestamp,
                                'op': 'set',
                                'oldValue': o,
                                'newValue': n,
                            }
                        )
                        return
                for i, (oi, ni) in enumerate(zip(o, n)):
                    walk(join_id(cur_id, str(i)), oi, ni)
            else:
                changes.append(
                    {
                        'id': cur_id,
                        'timestamp': timestamp,
                        'op': 'set',
                        'oldValue': o,
                        'newValue': n,
                    }
                )

        walk(base_id, old, new)
        return changes

    # FIXME this function looks strange. Can we make ut get_new_data and provide id with "/0" suffix for array,
    # and do not look intho block child attribute?
    def get_new_item_data(self, resource_id: str, patch) -> Any:
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
            return self.render_data(res_block.child.new_data(patch))
        return None

    def archive_image_stats(self, image_id: str) -> Dict[str, Any]:
        """
        Color models and mipmaps of the other images of the archive (SHPI) holding the image `image_id`, so that the
        GUI can tell which choices the file already uses.

        Returns:
            {'images': n, 'color_models': {resource_id: count}, 'with_mipmaps': n}
        """
        from resources.eac.bitmaps import EacImage

        import re

        # <archive>__children/<i>/item/data or <archive>/children/<i>/item/data
        match = re.match(r'^(.*)(?:__|/)children/(\d+)/item/data$', image_id)
        if not match:
            return {'images': 0, 'color_models': {}, 'with_mipmaps': 0}
        archive_id, own_index = match.group(1), match.group(2)
        (_, archive_block, archive), _ = require_resource(archive_id)
        possible_blocks = getattr(getattr(archive_block, 'item_block', None), 'possible_blocks', [])
        stats = {'images': 0, 'color_models': {}, 'with_mipmaps': 0}
        for i, child in enumerate(archive.get('children', [])):
            if str(i) == own_index:
                continue
            item = child['item']
            if item is None or not isinstance(possible_blocks[item['choice_index']], EacImage):
                continue
            stats['images'] += 1
            resource_id = item['data']['resource_id']
            stats['color_models'][resource_id] = stats['color_models'].get(resource_id, 0) + 1
            stats['with_mipmaps'] += item['data'].get('mipmaps') is not None
        return stats

    def palette_usage(self, palette_id: str) -> List[int]:
        """
        Indices of the palette `palette_id` the 8Bit images using it hold: the image of an embedded palette, or the
        images of the SHPI which take this palette item (by name, `determine_palette_for_8_bit_bitmap`)

        Returns:
            sorted indices
        """
        import re

        from resources.eac.bitmaps import EacImage
        from resources.eac.utils import determine_palette_for_8_bit_bitmap

        (_, _, palette), _ = require_resource(palette_id)
        images = []
        if palette_id.endswith('/embedded_palette'):
            image_id = palette_id[: -len('/embedded_palette')]
            (_, image_block, image), _ = require_resource(image_id)
            images.append(image)
        else:
            match = re.match(r'^(.*)(?:__|/)children/\d+/item/data$', palette_id)
            if not match:
                return []
            (_, archive_block, archive), _ = require_resource(match.group(1))
            possible_blocks = getattr(getattr(archive_block, 'item_block', None), 'possible_blocks', [])
            for i, child in enumerate(archive.get('children', [])):
                item = child['item']
                if item is None or not isinstance(possible_blocks[item['choice_index']], EacImage):
                    continue
                image = item['data']
                if image.get('resource_id') != '8Bit':
                    continue
                image_id = join_id(match.group(1), 'children', str(i), 'item', 'data')
                _, used_palette = determine_palette_for_8_bit_bitmap(
                    possible_blocks[item['choice_index']], image, image_id
                )
                if used_palette is palette:
                    images.append(image)
        used = set()
        for image in images:
            if image.get('resource_id') == '8Bit':
                used.update(image['bitmap'])
                used.update(image.get('mipmaps') or [])
        return sorted(used)

    def get_trailing_optional_field_data(self, resource_id: str) -> Any:
        """
        Get freshly-created data for a `TrailingOptionalBlock` field itself (as opposed to
        `get_new_item_data`, which creates a new *item* for a container found under an optional
        field). Used by the GUI's presence checkbox when the user turns a currently-absent
        (`None`) trailing field on.

        Args:
            resource_id: ID of the `TrailingOptionalBlock` field

        Returns:
            `child.new_data()` for that field, or `None` if it isn't a `TrailingOptionalBlock`
        """
        (_, res_block, _) = require_resource(resource_id)[0]
        if not isinstance(res_block, TrailingOptionalBlock):
            return None
        return self.render_data(res_block.child.new_data())
