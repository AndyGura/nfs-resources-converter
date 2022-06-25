from abc import ABC
from io import BufferedReader

import settings
from buffer_utils import read_byte
from parsers.resources.base import BaseResource
from utils import my_import


# TODO remove temporary class for migrating parsers logic
class ReadBlockWrapper(BaseResource, ABC):
    block_class = None
    resource = None

    def __init__(self, *args, block_class, **kwargs):
        super().__init__(*args, **kwargs)
        self.block_class = block_class

    def read(self, buffer: BufferedReader, length: int, path: str = None) -> int:
        start = buffer.tell()
        self.resource = self.block_class()
        self.resource.read(buffer, length)
        bytes_consumed = buffer.tell() - start
        if bytes_consumed < length:
            self.unknowns.append({'trailing_bytes': [read_byte(buffer) for _ in range(length - bytes_consumed)]})
        return length

    def save_converted(self, path: str):
        serializer_class_name = settings.SERIALIZER_CLASSES.get(self.block_class.__name__)
        serializer_class = None
        if serializer_class_name:
            try:
                serializer_class = my_import(f'serializers.{serializer_class_name}')
            except ImportError:
                pass
        if not serializer_class_name or not serializer_class:
            raise NotImplementedError(f'Serializer for resource {self.block_class.__name__} not implemented!')
        serializer = serializer_class()
        serializer.serialize(self.resource, path)
