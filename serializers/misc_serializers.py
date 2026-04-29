from typing import List

from serializers import BaseFileSerializer


class ShpiTextSerializer(BaseFileSerializer):

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs) -> List[str]:
        super().serialize(data, path)
        with open(f'{path}.txt', 'w') as file:
            file.write(data['text'])
        return [f'{path}.txt']
