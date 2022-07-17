import json

from library.helpers.json import rec_dd, resource_to_json
from library.read_blocks.compound import CompoundBlock
from serializers import BaseFileSerializer


class JsonSerializer(BaseFileSerializer):

    def serialize(self, block: CompoundBlock, path: str):
        super().serialize(block, path)
        res = rec_dd()
        for key, value in block.persistent_data.items():
            if isinstance(block, CompoundBlock) and key in block.Fields.unknown_fields:
                continue
            key_parts = key.split('__')
            dictionary = res
            for sub_key in key_parts[:-1]:
                dictionary = res[sub_key]
            dictionary[key_parts[-1]] = resource_to_json(value)
        json_str = json.dumps(res, indent=4)
        with open(f'{path}.json', 'w') as file:
            file.write(json_str)
