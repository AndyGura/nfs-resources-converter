from io import BufferedReader, BytesIO

from library.read_blocks.atomic import Utf8Field
from library.read_blocks.data_wrapper import DataWrapper


class DashDeclarationFile(Utf8Field):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.persistent_data = None

    def read(self, buffer: [BufferedReader, BytesIO], size: int, parent_read_data: dict = None):
        res = super().read(buffer, size, parent_read_data)
        self.persistent_data = res
        return res

    def from_raw_value(self, raw: bytes):
        text = super().from_raw_value(raw)
        dictionary = {}
        values = text.split('\n')
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
        return DataWrapper(dictionary)

    def to_raw_value(self, value) -> bytes:
        raise NotImplementedError
