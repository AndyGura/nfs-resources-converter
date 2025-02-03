import traceback
from io import BufferedReader, BytesIO
from typing import List, Dict, Tuple, Any

import settings
from library.context import ReadContext, WriteContext, DocumentationContext
from library.exceptions import DataIntegrityException
from library.read_blocks.basic import DataBlock, SkipBlock, BytesBlock
from library.utils.id import join_id


class DelegateBlock(DataBlock):

    def __init__(self, possible_blocks: List[DataBlock], choice_index=None, **kwargs):
        super().__init__(**kwargs)
        self.possible_blocks = possible_blocks
        self.choice_index = choice_index

    @property
    def schema(self) -> Dict:
        choice_index_doc = self.choice_index
        if isinstance(choice_index_doc, tuple):
            (_, choice_index_doc) = choice_index_doc
        if callable(choice_index_doc):
            try:
                choice_index_doc = str(choice_index_doc(DocumentationContext()))
            except:
                choice_index_doc = 'custom_func'
        return {
            **super().schema,
            'possible_resource_schemas': [block.schema for block in self.possible_blocks],
            'choice_index': choice_index_doc,
        }

    # For auto-generated documentation only
    @property
    def size_doc_str(self):
        int_min = None
        int_max = 0
        for size_doc in [x.size_doc_str for x in self.possible_blocks]:
            try:
                size = int(size_doc)
                int_min = min(int_min, size) if int_min is not None else size
                int_max = max(int_max, size)
            except ValueError:
                splt = size_doc.split('..')
                if len(splt) == 2:
                    try:
                        int_min = min(int_min, int(splt[0])) if int_min is not None else int(splt[0])
                    except ValueError:
                        return '?'
                    if int_max < float('Inf'):
                        try:
                            int_max = max(int_max, int(splt[1]))
                        except ValueError:
                            int_max = float('Inf')
                else:
                    return '?'
        if int_min == int_max:
            return str(int_min)
        if int_max == float('Inf'):
            if int_min == 0:
                return '?'
            return f'{int_min}..?'
        return f'{int_min}..{int_max}'

    def get_child_block_with_data(self, unpacked_data, name: str) -> Tuple['DataBlock', Any]:
        # data path should always contain definition of selected delegate option and data for selected option.
        # The only valid name provided to get_child_block_with_data here is data
        assert name == 'data'
        return self.possible_blocks[unpacked_data['choice_index']], unpacked_data['data']

    def new_data(self):
        return {'choice_index': 0,
                'data': self.possible_blocks[0].new_data()}

    def read(self, buffer: [BufferedReader, BytesIO], ctx: ReadContext = DataBlock.root_read_ctx, name: str = '',
             read_bytes_amount=None):
        delegated_block_index = self.choice_index
        if isinstance(delegated_block_index, tuple):
            # cut off the documentation
            (delegated_block_index, _) = delegated_block_index
        if callable(delegated_block_index):
            delegated_block_index = delegated_block_index(ctx, name=name)
        return {
            'choice_index': delegated_block_index,
            'data': self.possible_blocks[delegated_block_index].read(buffer, ctx=ctx, name=name,
                                                                     read_bytes_amount=read_bytes_amount)
        }

    def estimate_packed_size(self, data, ctx: WriteContext = None):
        delegated_block, data = self.possible_blocks[data['choice_index']], data['data']
        return delegated_block.estimate_packed_size(data, ctx=ctx)

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        delegated_block, data = self.possible_blocks[data['choice_index']], data['data']
        return delegated_block.write(data, ctx=ctx, name=name)

    def validate_after_read(self, value, ctx: ReadContext = DataBlock.root_read_ctx, name: str = ''):
        delegated_block, data = self.possible_blocks[value['choice_index']], value['data']
        return delegated_block.validate_after_read(data, ctx=ctx, name=name)


class AutoDetectBlock(DelegateBlock):

    def __init__(self, **kwargs):
        super().__init__(choice_index=self.detect, **kwargs)

    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'choice_index': 'Auto-detect'
        }

    def detect(self, ctx, name=None):
        from library import probe_block_class
        exc = None
        block_class = None
        try:
            file_path = ctx.ctx_path
            if name and not file_path.endswith(name):
                file_path = join_id(file_path, name)
            block_class = probe_block_class(ctx.buffer,
                                            file_path=file_path,
                                            resources_to_pick=[x.__class__ for x in self.possible_blocks])
        except NotImplementedError as ex:
            exc = ex
        for (i, block) in enumerate(self.possible_blocks):
            match = (isinstance(block, block_class)
                     if block_class
                     else (isinstance(block, SkipBlock) or isinstance(block, BytesBlock)))
            if match:
                if isinstance(block, SkipBlock) and block.error_strategy == "return_exception":
                    block.exception = exc  # TODO do not write to block!
                return i
        raise DataIntegrityException(ctx=ctx,
                                     message='Expectation failed for auto-detect block while reading: class not found')


def _enum_lookup(ctx, enum_field, fallback_index):
    try:
        return [name for (_, name) in ctx.relative_block(enum_field).enum_names].index(ctx.data(enum_field))
    except Exception:
        if settings.print_errors:
            traceback.print_exc()
        return fallback_index


class EnumLookupDelegateBlock(DelegateBlock):

    def __init__(self, enum_field: str, blocks: List[DataBlock], **kwargs):
        super().__init__(possible_blocks=blocks,
                         choice_index=(lambda ctx, **_: _enum_lookup(ctx, enum_field, len(blocks) - 1),
                                       f'According to enum {enum_field}'),
                         **kwargs)
        self.enum_field = enum_field

