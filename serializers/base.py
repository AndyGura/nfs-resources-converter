import os
from abc import ABC, abstractmethod
from os.path import getsize
from typing import Dict

import settings
from library.utils.class_dict import ClassDict
from library.utils.id import join_id


class ResourceSerializer(ABC):
    settings = ClassDict.wrap(settings.__dict__.copy())

    def patch_settings(self, settings_patch: dict):
        self.settings.update(settings_patch)

    def setup_for_reversible_serialization(self) -> bool:
        return False

    @abstractmethod
    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs):
        raise NotImplementedError

    def deserialize(self, path: str, id=None, block=None, **kwargs):
        raise NotImplementedError


class DelegateBlockSerializer(ResourceSerializer):

    def is_dir(self, block, data):
        from serializers import get_serializer
        sub_block, sub_data = block.possible_blocks[data['choice_index']], data['data']
        serializer = get_serializer(sub_block, sub_data)
        return serializer.is_dir

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs) -> Dict:
        from serializers import get_serializer
        sub_block, sub_data = block.possible_blocks[data['choice_index']], data['data']
        serializer = get_serializer(sub_block, sub_data)
        return serializer.serialize(sub_data, path=path, id=join_id(id, 'data'), block=sub_block)


class BaseFileSerializer(ResourceSerializer):

    def __init__(self, is_dir=False):
        self.is_dir = is_dir

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs):
        os.makedirs(path if self.is_dir else os.path.dirname(path), exist_ok=True)


class PlainBinarySerializer(BaseFileSerializer):

    def __init__(self):
        super().__init__(is_dir=False)

    def setup_for_reversible_serialization(self) -> bool:
        return True

    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs):
        if path.endswith('/') or path.endswith('\\'):
            path += id[id.rindex('/') + 1:]
        super().serialize(data, path)
        with open(f'{path}.bin', 'wb') as file:
            file.write(data)

    def deserialize(self, path: str, id=None, block=None, **kwargs):
        with open(f'{path}.bin', 'rb') as file:
            return file.read(getsize(f'{path}.bin'))
