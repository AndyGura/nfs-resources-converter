import json
from collections import defaultdict

from library.read_blocks import CompoundBlock
from serializers import BaseFileSerializer
from serializers.misc.json_utils import convert_bytes


def rec_dd():
    return defaultdict(rec_dd)


class JsonSerializer(BaseFileSerializer):

    # data is already valid dict, but we want to filter out unknown fields here
    def __make_dict(self, block, data):
        res = rec_dd()
        for key, value in data.items():
            if isinstance(block, CompoundBlock) and block.field_extras_map[key].get('is_unknown'):
                continue
            try:
                value_block, value = block.get_child_block_with_data(data, key)
            except AttributeError:
                value_block = None
            if isinstance(value_block, CompoundBlock):
                res[key] = self.__make_dict(value_block, value)
            else:
                res[key] = value
        return res

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs):
        super().serialize(data, path)
        json_str = json.dumps(convert_bytes(self.__make_dict(block, data)), indent=4)
        if path.endswith('/') or path.endswith('\\'):
            path += id[id.rindex('/') + 1:]
        with open(f'{path}.json', 'w') as file:
            file.write(json_str)
