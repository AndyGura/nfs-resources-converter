import re
from typing import Union, Callable, Dict, Any, Tuple, Optional
from library.context import ReadContext, WriteContext, DocumentationContext
from library.read_blocks.basic import DataBlock

Criteria = Union[Callable[[Union[ReadContext, WriteContext]], bool], Tuple[Callable[[Union[ReadContext, WriteContext]], bool], str]]


class OptionalBlock(DataBlock):
    """
    A field that is only present when `criteria(ctx)` holds, backed by data that already
    describes its own presence identically while reading and while writing - a version number,
    a flag bit, a pointer being non-zero, etc. (all available from `ctx.data(...)` on both the
    parsed tree and the tree about to be serialized).

    When the criteria is false, `default_value` (or `child.new_data()` if not given) stands in
    so the GUI always has a concrete value to show, and nothing is written to the buffer -
    `default_value` is silently discarded on write, it never round-trips.

    Not a fit for presence that can only be observed while reading (e.g. "there happens to be
    unused space left at the end of this structure"): `criteria` is re-evaluated at write time
    too, and a read-only fact like remaining buffer space isn't reconstructible from the data
    tree being written (`WriteContext` doesn't even expose it). Use `TrailingOptionalBlock` for
    that shape instead.
    """
    def __init__(self, child: DataBlock, criteria: Criteria, default_value=None, **kwargs):
        super().__init__(**kwargs)
        self.child = child
        self.criteria_label = None
        if isinstance(criteria, tuple):
            self.criteria = criteria[0]
            self.criteria_label = criteria[1]
        else:
            self.criteria = criteria
        if default_value is not None:
            self.default_value = default_value
        else:
            self.default_value = self.child.new_data()

    @property
    def size_doc_str(self):
        if re.fullmatch(r"^\d+\.\.[\d\\?]+$", self.child.size_doc_str):
            return f'0..{self.child.size_doc_str.split("..")[1]}'
        return f'0..{self.child.size_doc_str}'

    @property
    def schema(self) -> Dict:
        return {
            **self.child.schema,
            'is_optional': True,
            'criteria': self.criteria_label if self.criteria_label else str(self.criteria(DocumentationContext())),
        }

    def get_child_block_with_data(self, unpacked_data, name) -> Tuple['DataBlock', Any]:
        return self.child.get_child_block_with_data(unpacked_data, name)

    def new_data(self, patch = None):
        return self.default_value

    def read(self, ctx: ReadContext, name: str = '', read_bytes_amount=None):
        if self.criteria(ctx):
            return self.child.unpack(ctx, name, read_bytes_amount)
        return self.default_value

    def estimate_packed_size(self, data, ctx: WriteContext = None):
        if self.criteria(ctx):
            return self.child.estimate_packed_size(data, ctx)
        return 0

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        if self.criteria(ctx):
            return self.child.pack(data, ctx, name)
        return b''


DEFAULT_TRAILING_CRITERIA = (lambda ctx: ctx.read_bytes_remaining > 0, 'at least 1 byte remaining')


class TrailingOptionalBlock(OptionalBlock):
    """
    A field that may or may not occupy free space left at the end of a structure or file - e.g.
    an optional trailing chunk that is only there if the surrounding container happened to leave
    enough bytes for it. `criteria` is plain read-time Python: it's handed the `ReadContext` and
    can do anything with it, from the default "at least 1 byte remaining" (`ctx.read_bytes_remaining
    > 0`), to comparing against a size the child itself can't tell you (its size may be static,
    but just as well unknown/variable), to peeking ahead and sniffing whether the upcoming bytes
    look like the expected format:

        def looks_like_mipmap(ctx):
            peeked = ctx.buffer.read(4)
            ctx.buffer.seek(-len(peeked), SEEK_CUR)  # undo the peek, reading must stay untouched
            return len(peeked) == 4 and peeked[0] in (0x78, 0x7e, 0x7d, ...)

    That's the intended way to parse a sequence of same-shaped-but-independently-optional trailing
    chunks whose relative order is known (e.g. bitmap mipmaps followed by an optional palette
    block): stack consecutive `TrailingOptionalBlock` fields, each peeking for its own signature.

    Whether `criteria` holds isn't something `write` can recompute - by the time we're writing,
    there's no buffer left to consult (`WriteContext` doesn't even expose `read_bytes_remaining`),
    so `criteria` is never invoked at write time. Instead, presence is carried by the value itself:
    absence reads back as `None` (not `child.new_data()` - fabricating child data here would make
    an untouched round-trip write bytes that were never in the source), and writing skips the
    field whenever the value is `None`, writes the child in full otherwise. This also means
    `new_data()` (used by the GUI's "create new item" flow) produces `None`: a freshly-created
    instance has no way to know whether space/signature would be there for it.

    The GUI renders this as its own component (a presence checkbox wrapping the child's own
    editor) rather than transparently impersonating the child like `OptionalBlock` does, since a
    `None` value has to be toggleable by hand instead of just displayed.
    """
    def __init__(self, child: DataBlock, criteria: Optional[Criteria] = None, **kwargs):
        kwargs.pop('default_value', None)
        super().__init__(child=child, criteria=criteria or DEFAULT_TRAILING_CRITERIA, **kwargs)
        # Absence must stay a real "no data" marker rather than OptionalBlock's usual
        # child.new_data() fallback - see class docstring.
        self.default_value = None

    @property
    def schema(self) -> Dict:
        # Unlike OptionalBlock, don't impersonate the child's schema: this block gets its own GUI
        # component (see class docstring), so it needs its own identity in block_class_mro. The
        # child's schema is still exposed, just nested instead of spread at the top level.
        return {
            # Skip OptionalBlock.schema (which spreads the child's schema in place of its own) -
            # go straight to DataBlock's, so block_class_mro names this class, not the child's.
            **super(OptionalBlock, self).schema,
            'is_optional': True,
            'criteria': self.criteria_label if self.criteria_label else str(self.criteria(DocumentationContext())),
            'child_schema': self.child.schema,
        }

    def estimate_packed_size(self, data, ctx: WriteContext = None):
        if data is None:
            return 0
        return self.child.estimate_packed_size(data, ctx)

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        if data is None:
            return b''
        return self.child.pack(data, ctx, name)
