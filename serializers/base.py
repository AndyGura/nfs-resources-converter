import os
from abc import ABC, abstractmethod
from typing import Dict, Any

import settings
from library.helpers.data_wrapper import DataWrapper
from library.helpers.id import join_id


class ResourceSerializer(ABC):
    settings = DataWrapper.wrap(settings.__dict__.copy())

    def patch_settings(self, settings_patch: dict):
        self.settings.update(settings_patch)

    def setup_for_reversible_serialization(self) -> bool:
        return False

    @abstractmethod
    def serialize(self, data: dict, path: str, id=None, block=None, **kwargs) -> Dict:
        raise NotImplementedError

    def deserialize(self, data: Any, path: str, id=None, block=None, **kwargs):
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
