"""Lazy parts of a parsed resource tree.

When a file is read with `ReadContext.lazy` set (`require_file` does it by default), archive entries and chunks of
chunk bundles are not parsed. They are `LazyDict`s: real dicts which hold only a few values known from the header
(the "seed", e.g. alias or chunk id) and a `Slot` pointing to their bytes. Reading any other key parses the part once,
from the same bytes and with the same read context chain as an eager read would, and fills the same object, so later
reads are plain dict lookups. A part which was never loaded is written back as its original bytes.

    archive['children'][1]                     # LazyDict, nothing parsed
    archive['children'][1]['alias']            # seeded value, nothing parsed
    archive['children'][1]['item']['data']     # parses entry 1 only

Everything which reads a whole dict (iteration, `items()`, `dict(x)`, `json.dumps`, `==`, `copy`, `pickle`) loads it
first, so code unaware of laziness gets complete data. `copy.deepcopy` of an unloaded part is an unloaded twin on the
same slot, and two unloaded parts on the same slot are equal without parsing.
"""

import os
import threading
from contextlib import contextmanager
from copy import deepcopy
from io import BytesIO
from typing import Any, Callable, Dict, FrozenSet, Optional

# one lock for all deferred parses: they reuse open file handles and the shared context tree
LOAD_LOCK = threading.RLock()

# counters for tests and profiling
stats = {'parses': 0}


class FileChangedError(Exception):
    pass


class SourceClosedError(Exception):
    pass


class MemorySource:
    """Bytes in memory, e.g. decompressed QFS / JDLZ data"""

    def __init__(self, data: bytes):
        self.data = data

    @contextmanager
    def open(self):
        yield BytesIO(self.data)


class FileSource:
    """A file on disk. A handle is opened on the first deferred read and kept open. Raises `FileChangedError` if the
    file was modified since it was read, and `SourceClosedError` after `close()` (the file was saved or closed)"""

    def __init__(self, path: str):
        self.path = path
        st = os.stat(path)
        self.size, self.mtime_ns = st.st_size, st.st_mtime_ns
        self._handle = None
        self.closed = False

    @contextmanager
    def open(self):
        if self.closed:
            raise SourceClosedError(f'File {self.path} was closed or saved, reload it to read its unloaded parts')
        st = os.stat(self.path)
        if (st.st_size, st.st_mtime_ns) != (self.size, self.mtime_ns):
            raise FileChangedError(f'File {self.path} was changed on disk, reload it to read its unloaded parts')
        if self._handle is None or self._handle.closed:
            self._handle = open(self.path, 'rb')
        # a parse can trigger another deferred parse from the same file: restore the position for the outer one
        pos = self._handle.tell()
        try:
            yield self._handle
        finally:
            if not self._handle.closed:
                self._handle.seek(pos)

    def close(self):
        self.closed = True
        if self._handle is not None:
            self._handle.close()
            self._handle = None


_file_sources: Dict[str, FileSource] = {}


def open_file_source(path: str) -> FileSource:
    """New source for a file which is being read: replaces (and closes) the previous one for the same path"""
    close_file_source(path)
    source = FileSource(path)
    _file_sources[os.path.abspath(path)] = source
    return source


def close_file_source(path: str):
    """Lazy parts read from this file can't be loaded anymore. Called before the file is overwritten or when it is
    dropped from the file cache"""
    source = _file_sources.pop(os.path.abspath(path), None)
    if source is not None:
        source.close()


def source_for_buffer(buffer) -> Optional[Any]:
    """Source with the same bytes as a buffer being read, or None if the part can't be deferred"""
    if isinstance(buffer, BytesIO):
        source = getattr(buffer, '_lazy_source', None)
        if source is None:
            # `getvalue()` of a BytesIO made from bytes and never written to doesn't copy
            source = MemorySource(buffer.getvalue())
            buffer._lazy_source = source
        return source
    name = getattr(buffer, 'name', None)
    if isinstance(name, str):
        source = _file_sources.get(os.path.abspath(name))
        if source is not None and not source.closed:
            return source
    return None


class Slot:
    """Where an unloaded part is and how to parse it.
    `length` bytes at absolute `offset` are written back as they are while the part is unloaded. The first
    `item_length` of them are the part itself (the rest is padding owned by the part).
    `parse_fn(ctx, slot)` parses the part with `ctx` being a detached copy of `parent_ctx`, positioned at `offset`.
    `keys` are the keys the parsed dict will have (None if unknown), `seed` the values known without parsing"""

    __slots__ = ('source', 'offset', 'length', 'item_length', 'parse_fn', 'parent_ctx', 'keys', 'seed', 'args')

    def __init__(
        self,
        source,
        offset: int,
        length: int,
        parse_fn: Callable,
        parent_ctx,
        keys: Optional[FrozenSet[str]] = None,
        seed: Dict = None,
        item_length: int = None,
        args: Any = None,
    ):
        self.source = source
        self.offset = offset
        self.length = length
        self.item_length = length if item_length is None else item_length
        self.parse_fn = parse_fn
        self.parent_ctx = parent_ctx
        self.keys = keys
        self.seed = seed or {}
        self.args = args

    def parse(self) -> dict:
        with LOAD_LOCK, self.source.open() as buffer:
            stats['parses'] += 1
            ctx = self.parent_ctx.detached(buffer)
            buffer.seek(self.offset)
            return self.parse_fn(ctx, self)

    def raw(self) -> bytes:
        with LOAD_LOCK, self.source.open() as buffer:
            buffer.seek(self.offset)
            res = buffer.read(self.length)
        if len(res) < self.length:
            raise EOFError(f'Expected {self.length} bytes at {self.offset}, got {len(res)}')
        return res


class LazyDict(dict):
    """Dict parsed from its slot on first access to a key it doesn't hold yet, then a plain dict"""

    __slots__ = ('_slot', '_loaded')

    def __init__(self, slot: Slot):
        super().__init__(slot.seed)
        self._slot = slot
        self._loaded = False

    @property
    def slot(self) -> Slot:
        return self._slot

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def load(self) -> 'LazyDict':
        if not self._loaded:
            with LOAD_LOCK:
                if not self._loaded:
                    parsed = self._slot.parse()
                    # replace seeds as well: key order is the same as in eager read
                    dict.clear(self)
                    dict.update(self, parsed)
                    self._loaded = True
        return self

    def unload(self):
        """Drop parsed content (and any changes made to it), go back to the seeded state"""
        with LOAD_LOCK:
            dict.clear(self)
            dict.update(self, self._slot.seed)
            self._loaded = False

    def mark_loaded(self):
        """Treat current content as the loaded one, without parsing"""
        self._loaded = True

    # C-level dict.__getitem__ calls this for keys which are not in the dict yet
    def __missing__(self, key):
        if self._loaded:
            raise KeyError(key)
        return dict.__getitem__(self.load(), key)

    def get(self, key, default=None):
        if not self._loaded and not dict.__contains__(self, key):
            if self._slot.keys is not None and key not in self._slot.keys:
                return default
            self.load()
        return dict.get(self, key, default)

    def __contains__(self, key):
        if self._loaded or dict.__contains__(self, key):
            return dict.__contains__(self, key)
        if self._slot.keys is not None:
            return key in self._slot.keys
        return dict.__contains__(self.load(), key)

    def __len__(self):
        if not self._loaded and self._slot.keys is not None:
            return len(self._slot.keys)
        return dict.__len__(self.load())

    def __iter__(self):
        return dict.__iter__(self.load())

    def __reversed__(self):
        return dict.__reversed__(self.load())

    def keys(self):
        return dict.keys(self.load())

    def values(self):
        return dict.values(self.load())

    def items(self):
        return dict.items(self.load())

    def copy(self):
        return dict(dict.items(self.load()))

    def __copy__(self):
        return self.copy()

    def __setitem__(self, key, value):
        dict.__setitem__(self.load(), key, value)

    def __delitem__(self, key):
        dict.__delitem__(self.load(), key)

    def pop(self, *args):
        return dict.pop(self.load(), *args)

    def popitem(self):
        return dict.popitem(self.load())

    def setdefault(self, key, default=None):
        return dict.setdefault(self.load(), key, default)

    def update(self, *args, **kwargs):
        dict.update(self.load(), *args, **kwargs)

    def clear(self):
        # content is replaced as a whole (e.g. deserialized from a file): no need to parse the old one
        dict.clear(self)
        self._loaded = True

    def __or__(self, other):
        return dict.__or__(dict(dict.items(self.load())), other)

    def __ror__(self, other):
        return dict.__or__(other, dict(dict.items(self.load())))

    def __ior__(self, other):
        dict.update(self.load(), other)
        return self

    def __eq__(self, other):
        if (
            isinstance(other, LazyDict)
            and not self._loaded
            and not other._loaded
            and self._slot is other._slot
            and dict.__eq__(self, other)
        ):
            return True
        if isinstance(other, LazyDict):
            other.load()
        return dict.__eq__(self.load(), other)

    def __ne__(self, other):
        res = self.__eq__(other)
        return res if res is NotImplemented else not res

    __hash__ = None

    def __repr__(self):
        return dict.__repr__(self.load())

    def __deepcopy__(self, memo):
        if not self._loaded:
            twin = LazyDict(self._slot)
            # seeds could be changed in place
            dict.clear(twin)
            dict.update(twin, deepcopy(dict(dict.items(self)), memo))
            memo[id(self)] = twin
            return twin
        res = {}
        memo[id(self)] = res
        for k, v in dict.items(self):
            res[deepcopy(k, memo)] = deepcopy(v, memo)
        return res

    def __reduce_ex__(self, protocol):
        return dict, (dict(dict.items(self.load())),)


def is_loaded(node) -> bool:
    """False only for an unloaded `LazyDict`"""
    return not isinstance(node, LazyDict) or node._loaded


def load_all(tree):
    """Load every lazy part of a tree (in place) and return the tree"""
    stack = [tree]
    while stack:
        node = stack.pop()
        if isinstance(node, LazyDict):
            node.load()
        if isinstance(node, dict):
            stack.extend(v for v in dict.values(node) if isinstance(v, (dict, list)))
        elif isinstance(node, list):
            stack.extend(v for v in node if isinstance(v, (dict, list)))
    return tree


@contextmanager
def transient(node):
    """Load a lazy part for the duration of the block, then drop its parsed content again (changes made inside the
    block are dropped as well). Keeps memory at one part when walking a big file"""
    if not isinstance(node, LazyDict) or node._loaded:
        yield node
        return
    node.load()
    try:
        yield node
    finally:
        node.unload()


def lazy_unpack(
    block,
    ctx,
    name: str,
    length: int,
    read_bytes_amount=None,
    seed: Dict = None,
    keys: Optional[FrozenSet[str]] = None,
):
    """Read `block` at the buffer position, the way `block.unpack(ctx, name, read_bytes_amount)` does, but as an
    unloaded `LazyDict` if the context is lazy. `length` is the exact amount of bytes the block takes in the file: the
    buffer is moved past them. Returns parsed data as is if the context is not lazy"""
    if not getattr(ctx, 'lazy', False):
        return block.unpack(ctx, name, read_bytes_amount)
    source = source_for_buffer(ctx.buffer)
    if source is None:
        return block.unpack(ctx, name, read_bytes_amount)
    offset = ctx.buffer.tell()
    slot = Slot(
        source=source,
        offset=offset,
        length=length,
        parse_fn=_parse_block,
        parent_ctx=ctx,
        keys=keys if keys is not None else data_keys_of(block),
        seed=seed,
        args=(block, name, read_bytes_amount),
    )
    ctx.buffer.seek(offset + length)
    return LazyDict(slot)


def _parse_block(ctx, slot: Slot):
    block, name, read_bytes_amount = slot.args
    return block.unpack(ctx, name, read_bytes_amount)


def data_keys_of(block) -> Optional[FrozenSet[str]]:
    """Keys of data a block reads, if they are known without reading: compound blocks with generic read"""
    from library.read_blocks.compound import CompoundBlock

    if isinstance(block, CompoundBlock) and type(block).read is CompoundBlock.read:
        return frozenset(
            name
            for name, _ in block.field_blocks
            if (lambda usage: usage == 'everywhere' or 'io' in usage)(
                block.field_extras_map.get(name, {}).get('usage', 'everywhere')
            )
        )
    return None


def unloaded_slot(data) -> Optional[Slot]:
    """Slot of an unloaded part, None for anything else"""
    if isinstance(data, LazyDict) and not data._loaded:
        return data._slot
    return None
