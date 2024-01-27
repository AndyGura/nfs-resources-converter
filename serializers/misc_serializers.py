import json

from serializers import BaseFileSerializer


class ShpiTextSerializer(BaseFileSerializer):

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs):
        super().serialize(data, path, is_dir=False)
        with open(f'{path}.txt', 'w') as file:
            file.write(data['text'])
