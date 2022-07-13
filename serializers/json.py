import json
from collections import defaultdict

from parsers.resources.read_block_wrapper import ReadBlockWrapper
from resources.basic.compound_block import CompoundBlock
from serializers import BaseFileSerializer


def rec_dd():
    return defaultdict(rec_dd)


class JsonSerializer(BaseFileSerializer):

    def serialize(self, block: CompoundBlock, path: str):
        super().serialize(block, path)
        res = rec_dd()
        for key, value in block.persistent_data.items():
            if block.instance_fields_map[key].is_unknown:
                continue
            key_parts = key.split('__')
            dictionary = res
            for sub_key in key_parts[:-1]:
                dictionary = res[sub_key]
            dictionary[key_parts[-1]] = value.persistent_data if isinstance(value, CompoundBlock) else value
        with open(f'{path}.json', 'w') as file:
            file.write(json.dumps(res, indent=4))
