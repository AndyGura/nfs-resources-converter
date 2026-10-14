"""
Warnings and game compatibility checks over a read data tree, for the GUI.

Walks the block tree along with its data, calls `DataBlock.get_warnings` / `DataBlock.get_compatibility` of every
block on the way and returns the results with the resource id of the block (the same id the GUI uses). Subtrees
without a block that overrides the method are skipped, so files without checks cost next to nothing.
"""

import logging
from typing import Any, Dict, Iterator, List, Tuple

from library.context import CheckContext
from library.read_blocks import ArrayBlock, CompoundBlock, DataBlock, DelegateBlock, OptionalBlock
from library.read_blocks.misc.compatibility import Compatibility
from library.utils.id import join_id

_logger = logging.getLogger(__name__)


def _static_children(block: DataBlock) -> List[DataBlock]:
    if isinstance(block, CompoundBlock):
        return [field for _, field in block.field_blocks]
    if isinstance(block, ArrayBlock):
        return [block.child] if isinstance(block.child, DataBlock) else []
    if isinstance(block, DelegateBlock):
        return list(block.possible_blocks)
    if isinstance(block, OptionalBlock):
        return [block.child]
    return []


def _has_checks(block: DataBlock, method: str, visiting=None) -> bool:
    """Whether the block or any block below it overrides `method`. Cached on the block instance"""
    cache = block.__dict__.setdefault('_block_checks_cache', {})
    if method in cache:
        return cache[method]
    if getattr(type(block), method) is not getattr(DataBlock, method):
        cache[method] = True
        return True
    is_top = visiting is None
    visiting = set() if is_top else visiting
    if id(block) in visiting:
        # recursive block definition: the block on the way up decides
        return False
    visiting.add(id(block))
    res = any(_has_checks(child, method, visiting) for child in _static_children(block))
    visiting.discard(id(block))
    if is_top or res:
        # a False below the top can depend on a block still being visited
        cache[method] = res
    return res


def _children_with_data(block: DataBlock, data) -> Iterator[Tuple[str, DataBlock, Any]]:
    """(id part, child block, child data) of the block's children present in data. An empty id part = same id"""
    if isinstance(block, OptionalBlock):
        if data is not None:
            yield '', block.child, data
    elif isinstance(block, DelegateBlock):
        if isinstance(data, dict) and 'choice_index' in data:
            yield 'data', block.possible_blocks[data['choice_index']], data.get('data')
    elif isinstance(block, CompoundBlock):
        if isinstance(data, dict):
            for name, field in block.field_blocks:
                if name in data:
                    yield name, field, data[name]
    elif isinstance(block, ArrayBlock):
        if isinstance(data, list) and isinstance(block.child, DataBlock):
            for i, item in enumerate(data):
                yield str(i), block.child, item


def _walk(block: DataBlock, data, resource_id: str, ctx: CheckContext, method: str, visit):
    if block is None or not _has_checks(block, method):
        return
    if getattr(type(block), method) is not getattr(DataBlock, method):
        visit(block, data, resource_id, ctx)
    for part, child, child_data in _children_with_data(block, data):
        if child is None or not _has_checks(child, method):
            continue
        if part:
            child_ctx = CheckContext(name=part, data=child_data, block=child, parent=ctx)
            _walk(child, child_data, join_id(resource_id, part), child_ctx, method, visit)
        else:
            _walk(child, child_data, resource_id, ctx, method, visit)


def collect_warnings(block: DataBlock, data, name: str) -> List[Dict[str, str]]:
    """Warnings of the whole tree: [{id, message}], in tree order"""
    res = []

    def visit(b: DataBlock, d, resource_id: str, ctx: CheckContext):
        try:
            messages = b.get_warnings(d, ctx)
        except Exception as ex:
            _logger.exception(f'Warnings check failed at {resource_id}')
            messages = [f'Could not check this block: {ex.__class__.__name__}: {ex}']
        res.extend({'id': resource_id, 'message': m} for m in messages)

    _walk(block, data, name, CheckContext(name=name, data=data, block=block), 'get_warnings', visit)
    return res


def check_compatibility(block: DataBlock, data, name: str, game: str) -> Dict[str, Any]:
    """
    Compatibility of the whole tree with a game. Returns {game, state, results: [{id, state, message}]}, results
    leaving out blocks that don't know (unknown without a message). State: not compatible if any block is not,
    else compatible if any block is, else unknown
    """
    results = []

    def visit(b: DataBlock, d, resource_id: str, ctx: CheckContext):
        try:
            result = b.get_compatibility(d, game, ctx)
        except Exception as ex:
            _logger.exception(f'Compatibility check failed at {resource_id}')
            result = Compatibility.unknown(f'Could not check this block: {ex.__class__.__name__}: {ex}')
        if result.state != Compatibility.UNKNOWN or result.message:
            results.append({'id': resource_id, 'state': result.state, 'message': result.message})

    _walk(block, data, name, CheckContext(name=name, data=data, block=block), 'get_compatibility', visit)
    states = {r['state'] for r in results}
    if Compatibility.NOT_COMPATIBLE in states:
        state = Compatibility.NOT_COMPATIBLE
    elif Compatibility.COMPATIBLE in states:
        state = Compatibility.COMPATIBLE
    else:
        state = Compatibility.UNKNOWN
    return {'game': game, 'state': state, 'results': results}
