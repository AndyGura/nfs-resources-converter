import json
from collections import defaultdict
from typing import Iterable

from resources.basic.compound_block import CompoundBlock
from resources.basic.data_wrapper import DataWrapper
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
            dictionary[key_parts[-1]] = self._transform(value)
        json_str = json.dumps(res)#, indent=4) # TODO uncomment indent after finishing big refactoring
        with open(f'{path}.json', 'w') as file:
            file.write(json_str)

    def _transform(self, item):
        if isinstance(item, list):
            return [self._transform(x) for x in item]
        if isinstance(item, DataWrapper):
            return item.to_dict()
        if isinstance(item, Iterable):
            return dict(item)
        return item
