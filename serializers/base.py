import json
import os
from abc import ABC, abstractmethod
from typing import Dict

import settings
from library.read_blocks.array import ArrayBlock
from library.read_blocks.compound import CompoundBlock
from library.read_blocks.delegate import DelegateBlock
from library.read_data import ReadData


class ResourceSerializer(ABC):
    @abstractmethod
    def serialize(self, data: ReadData) -> Dict:
        raise NotImplementedError

    def deserialize(self, data: Dict) -> ReadData:
        raise NotImplementedError


class BaseFileSerializer(ResourceSerializer):

    def get_unknowns_dict(self, data: ReadData):
        if not isinstance(data, ReadData):
            return None
        from library.helpers.json import rec_dd, resource_to_json
        res = rec_dd()
        has_something = False
        if isinstance(data.block, CompoundBlock) and data.value is not None:
            for key, value in data.value.items():
                if key not in data.block.instance_fields_map:
                    continue
                if key in data.block.Fields.unknown_fields:
                    key_parts = key.split('__')
                    dictionary = res
                    for sub_key in key_parts[:-1]:
                        dictionary = res[sub_key]
                    dictionary[key_parts[-1]] = resource_to_json(value)
                    has_something = True
                elif isinstance(data.block.instance_fields_map[key], CompoundBlock):
                    sub_data = self.get_unknowns_dict(data.block.instance_fields_map[key])
                    if sub_data:
                        res[key] = sub_data
                        has_something = True
                elif isinstance(data.block.instance_fields_map[key], ArrayBlock):
                    custom_names = data[key].block_state.get('custom_names')
                    sub_data = {i: x for i, x in {i if custom_names is None else custom_names[i]: self.get_unknowns_dict(x) for i, x in enumerate(value)}.items() if x is not None}
                    if sub_data:
                        res[key] = sub_data
                        has_something = True
        return res if has_something else None

    def serialize(self, data: ReadData, path: str):
        os.makedirs('/'.join(path.split('/')[:-1]), exist_ok=True)
        block = data.block
        if isinstance(block, DelegateBlock):
            block = block.delegated_block
        if settings.export_unknown_values and isinstance(block, CompoundBlock):
            unknowns = self.get_unknowns_dict(data)
            if unknowns:
                with open(f'{path}{"__" if path.endswith("/") else ""}.unknowns.json', 'w') as file:
                    file.write(json.dumps(unknowns, indent=4))

    def deserialize(self, path: str, resource: ReadData) -> None:
        raise NotImplementedError
