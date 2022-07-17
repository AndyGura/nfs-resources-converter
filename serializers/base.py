import json
import os

import settings
from library.helpers.json import rec_dd, resource_to_json
from library.read_blocks.array import ArrayBlock
from library.read_blocks.compound import CompoundBlock
from library.read_blocks.delegate import DelegateBlock
from library.read_blocks.read_block import ReadBlock


class BaseFileSerializer:

    def __init__(self):
        self.current_serializing_block = None

    def get_unknowns_dict(self, block: CompoundBlock):
        res = rec_dd()
        has_something = False
        if isinstance(block, DelegateBlock):
            block = block.delegated_block
        if isinstance(block, CompoundBlock) and block.persistent_data is not None:
            for key, value in block.persistent_data.items():
                if key in block.Fields.unknown_fields:
                    key_parts = key.split('__')
                    dictionary = res
                    for sub_key in key_parts[:-1]:
                        dictionary = res[sub_key]
                    dictionary[key_parts[-1]] = resource_to_json(value)
                    has_something = True
                elif isinstance(block.instance_fields_map[key], CompoundBlock):
                    sub_data = self.get_unknowns_dict(block.instance_fields_map[key])
                    if sub_data:
                        res[key] = sub_data
                        has_something = True
                elif isinstance(block.instance_fields_map[key], ArrayBlock):
                    sub_data = {i: self.get_unknowns_dict(x) for i, x in enumerate(value)}
                    sub_data = {i: x for i, x in sub_data.items() if x is not None}
                    if sub_data:
                        res[key] = sub_data
                        has_something = True
        return res if has_something else None

    def serialize(self, block: ReadBlock, path: str):
        self.current_serializing_block = block
        os.makedirs('/'.join(path.split('/')[:-1]), exist_ok=True)
        if isinstance(block, DelegateBlock):
            block = block.delegated_block
        if settings.export_unknown_values and isinstance(block, CompoundBlock):
            unknowns = self.get_unknowns_dict(block)
            if unknowns:
                with open(f'{path}{"__" if path.endswith("/") else ""}.unknowns.json', 'w') as file:
                    file.write(json.dumps(unknowns, indent=4))

    def deserialize(self, path: str, block: ReadBlock):
        raise NotImplementedError
