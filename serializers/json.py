import json

from library.helpers.json import rec_dd, resource_to_json
from library.read_blocks.compound import CompoundBlock
from library.read_data import ReadData
from serializers import BaseFileSerializer


class JsonSerializer(BaseFileSerializer):

    def __make_dict(self, data: ReadData):
        res = rec_dd()
        for key, value in data.value.items():
            if isinstance(data.block, CompoundBlock) and key in data.block.Fields.unknown_fields:
                continue
            key_parts = key.split('__')
            dictionary = res
            for sub_key in key_parts[:-1]:
                dictionary = res[sub_key]
            if isinstance(value, ReadData) and isinstance(value.block, CompoundBlock):
                dictionary[key_parts[-1]] = self.__make_dict(value)
            else:
                dictionary[key_parts[-1]] = resource_to_json(value)
        return res

    def serialize(self, data: ReadData, path: str):
        super().serialize(data, path, is_dir=False)
        json_str = json.dumps(self.__make_dict(data), indent=4)
        if path.endswith('/') or path.endswith('\\'):
            path += data.id[data.id.rindex('/')+1:]
        with open(f'{path}.json', 'w') as file:
            file.write(json_str)
