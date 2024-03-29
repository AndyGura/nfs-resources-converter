from serializers import BaseFileSerializer


class ShpiTextSerializer(BaseFileSerializer):

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs):
        super().serialize(data, path)
        with open(f'{path}.txt', 'w') as file:
            file.write(data['text'])
