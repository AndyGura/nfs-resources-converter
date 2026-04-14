from abc import ABC
from typing import Dict, List, Tuple, Any, TypedDict, Union

from library.context import ReadContext, WriteContext
from library.exceptions import BlockDefinitionException, DataIntegrityException
from library.read_blocks.basic import DataBlock, DataBlockWithChildren
from library.read_blocks.numbers import IntegerBlock
from library.utils.docs import add_doc_numbers


class FieldExtras(TypedDict, total=False):
    """
    Extra metadata for declarative compound fields.
    Allowed optional keys:
      - description: str — Human-readable description of the field for docs/UI.
      - is_unknown: bool — Marks a field whose purpose/meaning is not fully known.
      - custom_offset: Union[int, str] — For documentation: shows how the field's offset is calculated
        if it is not placed sequentially. Accepts an absolute integer offset or an expression string.
      - usage: str — Where the field should be used. Possible values:
        -- coma-separated strings, e.g. 'ui,io'.
           Possible values are: 'ui', 'io', 'doc' for GUI editor, reading/writing data, and documentation, respectively.
        -- None or 'everywhere' (default) — used in IO, UI, and docs; same as 'ui,io,doc'
    """
    description: str
    is_unknown: bool
    custom_offset: Union[int, str]
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
            raise BlockDefinitionException(f'Cannot find field {name}')
        return field

    def get_child_block_with_data(self, unpacked_data: dict, name: str) -> Tuple['DataBlock', Any]:
        path = name.split('/')
        field = self.field_blocks_map.get(path[0])
        if field is None:
            raise BlockDefinitionException(f'Cannot find field {path[0]}')
        udata = unpacked_data.get(path[0])
        if len(path) > 1:
            return field.get_child_block_with_data(udata, '/'.join(path[1:]))
        else:
            return field, udata

    # For auto-generated documentation only
    @property
    def size_doc_str(self):
        acc = 0
        if callable(self.fields):
            return '?'
        for name, field in self.field_blocks:
            usage = self.field_extras_map.get(name, {}).get('usage', 'everywhere')
            if usage != 'everywhere' and 'io' not in usage:
                continue
            field_size_doc = field.size_doc_str
            acc = add_doc_numbers(acc, field_size_doc, show_expressions=False, produce_ranges=True)
        return acc

    def new_data(self):
        res = dict()
        for name, field in self.field_blocks:
            res[name] = field.new_data()
        return res

    def read(self, ctx: ReadContext, name: str = '', read_bytes_amount=None):
        res = dict()
        self_ctx = ctx.get_or_create_child(name, self, read_bytes_amount, res)
        for name, field in self.field_blocks:
            usage = self.field_extras_map.get(name, {}).get('usage', 'everywhere')
            if usage != 'everywhere' and 'io' not in usage:
                continue
            res[name] = field.unpack(ctx=self_ctx, name=name)
        return res

    def estimate_packed_size(self, data, ctx: WriteContext = None):
        self_ctx = WriteContext(data=data, block=self, parent=ctx)
        res = 0
        for name, field in self.field_blocks:
            usage = self.field_extras_map.get(name, {}).get('usage', 'everywhere')
            if usage != 'everywhere' and 'io' not in usage:
                continue
            res += field.estimate_packed_size(data=data.get(name), ctx=self_ctx)
        return res

    def offset_to_child_when_packed(self, data, child_name: str, ctx: WriteContext = None):
        self_ctx = WriteContext(data=data, block=self, parent=ctx)
        res = 0
        for name, field in self.field_blocks:
            usage = self.field_extras_map.get(name, {}).get('usage', 'everywhere')
            if usage != 'everywhere' and 'io' not in usage:
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
            if usage != 'everywhere' and 'io' not in usage:
                continue
            self_ctx.result += field.pack(data=data.get(name), ctx=self_ctx, name=name)
        return self_ctx.result


class SubByteCompoundBlock(IntegerBlock):

    ### schema type: (size, alias, type, details, description)
    ### example 1: (4, 'damage', 'number', [], 'Damage switch (0x8 means damaged)')
    ### example 2: (1, 'is_damaged', 'boolean', [], 'Flag is damaged')
    ### example 3: (2, 'test_enum', 'enum', ['A', 'B', 'C', 'D'], '...')
    def __init__(self, schema: List[Tuple[int, str, str, List[str], str]], **kwargs):
        super().__init__(**kwargs)
        self._schema_def = schema
        total_bits = sum(size for size, _, _, _, _ in schema)
        if total_bits != self.length * 8:
            raise BlockDefinitionException(f"SubByteCompoundBlock schema total bits ({total_bits}) "
                                           f"does not match length * 8 ({self.length * 8})")

    @property
    def schema(self) -> Dict:
        block_description = f'Sub-byte compound block'
        if self.length > 1:
            block_description += f' ({self.byte_order} endian)'
        block_description += ':'
        for size, alias, type_name, details, description in self._schema_def:
            if type_name == 'boolean':
                block_description += f'<br/>1-bit flag "{alias}"'
            elif type_name == 'number':
                block_description += f'<br/>{size}-bits int "{alias}"'
            elif type_name == 'enum':
                block_description += f'<br/>{size}-bits enum:'
                for i, v in enumerate(details):
                    block_description += f'<br/>&nbsp;&nbsp;- {i}: {v}'

        return {
            **super().schema,
            'block_description': block_description,
            'inline_description': True,
            'sub_byte_schema': [
                {
                    'size': size,
                    'alias': alias,
                    'type': type_name,
                    'details': details,
                    'description': description
                } for size, alias, type_name, details, description in self._schema_def
            ]
        }

    def new_data(self):
        res = {}
        for size, alias, type_name, details in self._schema_def:
            if type_name == 'boolean':
                res[alias] = False
            elif type_name == 'enum':
                res[alias] = details[0][1] if details else '0'
            else:
                res[alias] = 0
        return res

    def read(self, ctx: ReadContext, name: str = '', read_bytes_amount=None):
        raw_value = super().read(ctx, name, read_bytes_amount)
        res = {}
        current_bit = self.length * 8
        for size, alias, type_name, details, _ in self._schema_def:
            current_bit -= size
            value = (raw_value >> current_bit) & ((1 << size) - 1)
            if type_name == 'boolean':
                res[alias] = bool(value)
            elif type_name == 'enum':
                mapping = {i: v for i, v in enumerate(details)}
                res[alias] = mapping.get(value, str(value))
            else:
                res[alias] = value
        return res

    def estimate_packed_size(self, data, ctx: WriteContext = None):
        return self.length

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        res = 0
        current_bit = self.length * 8
        for size, alias, type_name, details, _ in self._schema_def:
            current_bit -= size
            value = data.get(alias)
            if type_name == 'boolean':
                int_val = 1 if value else 0
            elif type_name == 'enum':
                mapping = {v: i for i, v in enumerate(details)}
                try:
                    int_val = mapping[value]
                except KeyError:
                    int_val = int(value)
            else:
                int_val = int(value)
            res |= (int_val & ((1 << size) - 1)) << current_bit
        return super().write(res, ctx, name)

class BitFlagsBlock(SubByteCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {**super().schema,
                'flag_names': self.flag_name_map,
                'block_description': f'{self.length * 8} flags container<br/><details><summary>flag names (from least to most significant)</summary>'
                                     + '<br/>'.join(
                    [f'{i}: {x}' for i, x in enumerate(self.flag_name_map) if x != str(i)]) + '</details>'}

    def __init__(self, flag_names: List[Tuple[int, str]], **kwargs):
        self.flag_names = flag_names
        length = kwargs.pop('length', None)
        if length is None:
            raise Exception('BitFlagsBlock requires length')
        schema = []
        self.flag_name_map = [str(i) for i in range(length * 8)]
        for value, name in self.flag_names:
            self.flag_name_map[value] = name
        for i in range(length * 8 - 1, -1, -1):
            schema.append((1, self.flag_name_map[i], 'boolean', '', ''))
        super().__init__(length=length, schema=schema, **kwargs)


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
