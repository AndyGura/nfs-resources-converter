import json

from library.helpers.json import rec_dd, resource_to_json
from library.read_blocks.compound import CompoundBlock
from library.read_blocks.delegate import DelegateBlock
from serializers import BaseFileSerializer


class JsonSerializer(BaseFileSerializer):

    def __make_dict(self, block):
        if isinstance(block, DelegateBlock):
            block = block.delegated_block
        res = rec_dd()
        for key, value in block.persistent_data.items():
            if isinstance(block, CompoundBlock) and key in block.Fields.unknown_fields:
                continue
            key_parts = key.split('__')
            dictionary = res
            for sub_key in key_parts[:-1]:
                dictionary = res[sub_key]
            if isinstance(value, CompoundBlock) or (isinstance(value, DelegateBlock) and isinstance(value.delegated_block, CompoundBlock)):
                dictionary[key_parts[-1]] = self.__make_dict(value)
            else:
                dictionary[key_parts[-1]] = resource_to_json(value)
        return res

    def serialize(self, block: CompoundBlock, path: str):
        super().serialize(block, path)
        json_str = json.dumps(self.__make_dict(block), indent=4)
        with open(f'{path}.json', 'w') as file:
            file.write(json_str)
