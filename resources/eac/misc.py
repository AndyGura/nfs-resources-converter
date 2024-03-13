from io import BufferedReader, BytesIO
from typing import Dict

from library.context import WriteContext, ReadContext
from library.read_blocks import DeclarativeCompoundBlock, IntegerBlock, BytesBlock, UTF8Block, DataBlock


class ShpiText(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'An entry, which sometimes can be seen in the SHPI archive block after bitmap, '
                                 'contains some text. The purpose is unclear',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (IntegerBlock(length=1, required_value=0x6F),
                       {'description': 'Resource ID'})
        unk = (BytesBlock(length=3),
               {'is_unknown': True})
        length = (IntegerBlock(length=4),
                  {'description': 'Text length'})
        text = (UTF8Block(length=(lambda ctx: ctx.data('length'), 'length')),
                {'description': 'Text itself'})


class DashDeclarationFile(UTF8Block):

    def __init__(self, **kwargs):
        super().__init__(length=0, **kwargs)

    def read(self, buffer: [BufferedReader, BytesIO], ctx: ReadContext = DataBlock.root_read_ctx, name: str = '',
             read_bytes_amount=None):
        self._length = read_bytes_amount
        text = super().read(buffer, ctx, name, read_bytes_amount)
        dictionary = {}
        values = text.splitlines()
        current_key = None
        current_key_ended = True
        for value in values:
            if value.startswith('#'):
                if not current_key_ended:
                    raise Exception(f'Unexpected new key {value}. Last key not finished')
                current_key = value[1:]
                current_key_ended = False
                continue
            if value == '':
                if not dictionary.get(current_key):
                    dictionary[current_key] = []
                current_key_ended = True
                continue
            if not current_key:
                raise Exception(f'Cannot parse value {value}. Unknown key')
            if dictionary.get(current_key) is not None:
                if current_key_ended:
                    dictionary[current_key].append([value])
                    current_key_ended = False
                else:
                    dictionary[current_key][-1].append(value)
            else:
                value = value.split(' ')
                value = value[0] if len(value) == 1 else value
                dictionary[current_key] = value if not current_key_ended else [value]
        return dictionary

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        raise NotImplementedError
