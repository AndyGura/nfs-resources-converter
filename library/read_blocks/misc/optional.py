from typing import Union, Callable, Dict, Any, Tuple
from library.context import ReadContext, WriteContext, DocumentationContext
from library.read_blocks.basic import DataBlock


class OptionalBlock(DataBlock):
    def __init__(self, child: DataBlock, criteria: Union[Callable[[Union[ReadContext, WriteContext]], bool], Tuple[Callable[[Union[ReadContext, WriteContext]], bool], str]], default_value=None, **kwargs):
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

    def new_data(self):
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
