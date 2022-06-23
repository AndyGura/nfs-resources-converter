import json

import settings
from resources.fields import ReadBlock


class BaseFileSerializer:

    def serialize(self, block: ReadBlock, path: str):
        if settings.save_unknown_values:
            unknown_data = {}
            # TODO put unknown data to dict
            if unknown_data:
                with open(f'{path}__unknowns.json', 'w') as file:
                    file.write(json.dumps(unknown_data, indent=4))

    def deserialize(self, path: str, block: ReadBlock):
        raise NotImplementedError
