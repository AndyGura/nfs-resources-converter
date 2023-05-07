from library.helpers.data_wrapper import DataWrapper
from library.read_blocks.atomic import Utf8Block
from library.read_data import ReadData


class DashDeclarationFile(Utf8Block):

    def from_raw_value(self, raw: bytes, state: dict):
        text = super().from_raw_value(raw, state)
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
        return DataWrapper(dictionary)

    def to_raw_value(self, data: ReadData) -> bytes:
        raise NotImplementedError
