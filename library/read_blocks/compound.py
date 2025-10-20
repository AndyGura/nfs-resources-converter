from abc import ABC
from io import BufferedReader, BytesIO
from typing import Dict, List, Tuple, Any, TypedDict, Optional, Callable, Union

from library.context import ReadContext, WriteContext
from library.exceptions import BlockDefinitionException, DataIntegrityException
from library.read_blocks.basic import DataBlock, DataBlockWithChildren


class FieldExtras(TypedDict, total=False):
    """
    Extra metadata for declarative compound fields.
    Allowed optional keys:
      - description: str — Human-readable description of the field for docs/UI.
      - is_unknown: bool — Marks a field whose purpose/meaning is not fully known.
      - custom_offset: Union[int, str] — For documentation: shows how the field's offset is calculated
        if it is not placed sequentially. Accepts an absolute integer offset or an expression string.
      - programmatic_value: Callable[[WriteContext], Any] — Function to compute the value at write time;
        if present, the field value in the input data is ignored and this callable is used instead.
      - usage: str — Where the field should be used. Allowed values:
        'everywhere' (default) — used in IO, UI, and docs;
        'ui_only' — shown only in UI; ignored for IO and docs;
        'skip_ui' — used in IO and docs but hidden in UI.
    """
    description: str
    is_unknown: bool
    custom_offset: Union[int, str]
    programmatic_value: Callable[[WriteContext], Any]
    usage: str

class CompoundBlock(DataBlockWithChildren, DataBlock, ABC):

    # accepts list of fields. Field should be declared as tuple (name, block, extras)
    def __init__(self, fields: List[Tuple[str, DataBlock, FieldExtras]], inline_description: str = None,
                 **kwargs):
        super().__init__(**kwargs)
        self.fields = fields
        self.inline_description = inline_description
        self.field_blocks = [(name, instance) for (name, instance, _) in self.fields]
        self.field_blocks_map = {name: res for (name, res, _) in self.fields}
        self.field_extras_map = {name: extra for (name, _, extra) in self.fields}

    @property
    def schema(self) -> Dict:
        schema = {
            **super().schema,
            'block_description': '',
            'inline_description': False,
            'fields': [
                {
                    'name': name,
                    'schema': field.schema,
                    'is_programmatic': self.field_extras_map
                                       .get(name, {}).get('programmatic_value') is not None,
                    'is_unknown': self.field_extras_map.get(name, {}).get('is_unknown', False),
                    'description': self.field_extras_map.get(name, {}).get('description', ''),
                    'usage': self.field_extras_map.get(name, {}).get('usage', 'everywhere'),
                } for name, field in self.field_blocks
            ] if self.fields else [],
        }
        if self.inline_description is not None:
            schema['inline_description'] = True
            schema['block_description'] = self.inline_description
        return schema

    def get_child_block(self, name: str) -> 'DataBlock':
        field = self.field_blocks_map.get(name)
        if field is None:
            raise BlockDefinitionException(None, f'Cannot find field {name}')
        return field

    def get_child_block_with_data(self, unpacked_data: dict, name: str) -> Tuple['DataBlock', Any]:
        field = self.field_blocks_map.get(name)
        if field is None:
            raise BlockDefinitionException(None, f'Cannot find field {name}')
        return field, unpacked_data.get(name)

    # For auto-generated documentation only
    @property
    def size_doc_str(self):
        min_acc = 0
        unknown_size = False

        if callable(self.fields):
            return '?'
        for name, field in self.field_blocks:
            usage = self.field_extras_map.get(name, {}).get('usage', 'everywhere')
            if usage == 'ui_only':
                continue
            field_size_doc = field.size_doc_str
            try:
                min_acc += int(field_size_doc)
            except ValueError:
                # if inner compound block with size range
                if '..?' in field_size_doc:
                    try:
                        min_acc += int(field_size_doc[:field_size_doc.index('..?')])
                    except:
                        pass
                unknown_size = True
        return str(min_acc) if not unknown_size else f'{min_acc}..?'

    def new_data(self):
        res = dict()
        for name, field in self.field_blocks:
            res[name] = field.new_data()
        return res

    def read(self, buffer: [BufferedReader, BytesIO], ctx: ReadContext = DataBlock.root_read_ctx, name: str = '',
             read_bytes_amount=None):
        res = dict()
        self_ctx = ReadContext(buffer=buffer, data=res, name=name, block=self, parent=ctx,
                               read_bytes_amount=read_bytes_amount)
        for name, field in self.field_blocks:
            usage = self.field_extras_map.get(name, {}).get('usage', 'everywhere')
            if usage == 'ui_only':
                continue
            res[name] = field.unpack(buffer=buffer, ctx=self_ctx, name=name)
        return res

    def estimate_packed_size(self, data, ctx: WriteContext = None):
        self_ctx = WriteContext(data=data, block=self, parent=ctx)
        res = 0
        for name, field in self.field_blocks:
            usage = self.field_extras_map.get(name, {}).get('usage', 'everywhere')
            if usage == 'ui_only':
                continue
            res += field.estimate_packed_size(data=data.get(name), ctx=self_ctx)
        return res

    def offset_to_child_when_packed(self, data, child_name: str, ctx: WriteContext = None):
        self_ctx = WriteContext(data=data, block=self, parent=ctx)
        res = 0
        for name, field in self.field_blocks:
            usage = self.field_extras_map.get(name, {}).get('usage', 'everywhere')
            if usage == 'ui_only':
                continue
            if name == child_name:
                return res
            res += field.estimate_packed_size(data=data.get(name), ctx=self_ctx)
        raise DataIntegrityException(ctx=ctx, message=f'Cannot calculate offset to child "{child_name}". '
                                                      f'Child with such name not found')

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        self_ctx = WriteContext(data=data, name=name, block=self, parent=ctx)
        self_ctx.result = bytes()
        for name, field in self.field_blocks:
            usage = self.field_extras_map.get(name, {}).get('usage', 'everywhere')
            if usage == 'ui_only':
                continue
            programmatic_value_func = self.field_extras_map.get(name, {}).get('programmatic_value')
            if programmatic_value_func is not None:
                val = programmatic_value_func(self_ctx)
            else:
                val = data.get(name)
            self_ctx.result += field.pack(data=val, ctx=self_ctx, name=name)
        return self_ctx.result


class CompoundBlockFields(ABC):
    @classmethod
    @property
    def fields(cls) -> List[Tuple[str, DataBlock]]:
        try:
            return cls.__fields_cache
        except AttributeError:
            cls.__fields_cache = [(key, value)
                                  for (key, value) in cls.__dict__.items()
                                  if isinstance(value, DataBlock) or (type(value) is tuple
                                                                      and isinstance(value[0], DataBlock))]
            return cls.__fields_cache


class DeclarativeCompoundBlock(CompoundBlock):
    class Fields(CompoundBlockFields):
        pass

    def __init__(self, **kwargs):
        super().__init__(fields=[(name, *declaration) if type(declaration) is tuple else (name, declaration, {}) for
                                 name, declaration
                                 in self.__class__.Fields.fields], **kwargs)
