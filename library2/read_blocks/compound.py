from abc import ABC
from io import BufferedReader, BytesIO
from typing import Dict, List, Tuple, Any

from library.helpers.exceptions import BlockDefinitionException
from library2.context import Context
from library2.read_blocks.basic import DataBlock


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


class CompoundBlock(DataBlock, ABC):
    class Fields(CompoundBlockFields):
        pass

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        fields = [(name, *declaration) if type(declaration) is tuple else (name, declaration, {}) for name, declaration
                  in self.__class__.Fields.fields]
        self.field_blocks = [(name, instance) for (name, instance, _) in fields]
        self.field_blocks_map = {name: res for (name, res, _) in fields}
        self.field_extras_map = {name: extra for (name, _, extra) in fields}

    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': '',
            'inline_description': False,
            'fields': [
                {
                    'name': name,
                    'schema': field.schema,
                    'is_programmatic': self.field_extras_map.get(name, {}).get('programmatic_value') is not None,
                    'is_unknown': self.field_extras_map.get(name, {}).get('is_unknown', False),
                } for name, field in self.field_blocks
            ],
        }

    def get_child_block(self, unpacked_data: dict, name: str) -> Tuple['DataBlock', Any]:
        for f_name, field in self.field_blocks:
            if f_name == name:
                return field, unpacked_data.get(name)
        raise BlockDefinitionException(f'Cannot find field {name}')

    # For auto-generated documentation only
    @property
    def size_doc_str(self):
        min_acc = 0
        unknown_size = False

        for _, field in self.field_blocks:
            field_size_doc = field.size_doc_str
            try:
                min_acc += int(field_size_doc)
            except ValueError:
                # if inner compound block with size range
                if '..?' in field_size_doc:
                    min_acc += int(field_size_doc[:field_size_doc.index('..?')])
                unknown_size = True
        return str(min_acc) if not unknown_size else f'{min_acc}..?'

    def read(self, buffer: [BufferedReader, BytesIO], ctx: Context = None, name: str = ''):
        res = dict()
        self_ctx = Context(buffer=buffer, data=res, name=name, parent=ctx)
        for name, field in self.field_blocks:
                res[name] = field.unpack(buffer=buffer, ctx=self_ctx, name=name)
        return res

    def write(self, data, ctx: Context = None, name: str = '') -> bytes:
        self_ctx = Context(data=data, name=name, parent=ctx)
        res = bytes()
        for name, field in self.field_blocks:
            programmatic_value_func = self.field_extras_map.get(name, {}).get('programmatic_value')
            if programmatic_value_func is not None:
                val = programmatic_value_func(self_ctx)
            else:
                val = data[name]
            res += field.pack(data=val, ctx=self_ctx, name=name)
        return res
