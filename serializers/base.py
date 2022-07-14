import json
import os

import settings
from resources.basic.read_block import ReadBlock


class BaseFileSerializer:

    def __init__(self):
        self.current_serializing_block = None

    def serialize(self, block: ReadBlock, path: str):
        self.current_serializing_block = block
        os.makedirs('/'.join(path.split('/')[:-1]), exist_ok=True)
        if settings.save_unknown_values:
            unknown_data = {}
            # TODO put unknown data to dict
            if unknown_data:
                with open(f'{path}{"__" if path.endswith("/") else ""}unknowns.json', 'w') as file:
                    file.write(json.dumps(unknown_data, indent=4))

    def deserialize(self, path: str, block: ReadBlock):
        raise NotImplementedError
