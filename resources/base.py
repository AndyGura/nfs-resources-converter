from abc import ABC
from functools import cached_property
from io import BufferedReader, BytesIO
from typing import List, Tuple, final

from resources.fields import ReadBlock


class BaseFields(ABC):
    @classmethod
    @property
    def fields(cls) -> List[Tuple[str, ReadBlock]]:
        try:
            return cls.__fields_cache
        except AttributeError:
            cls.__fields_cache = [(key, value) for (key, value) in cls.__dict__.items() if isinstance(value, ReadBlock)]
            return cls.__fields_cache


class BaseResource(ReadBlock, ABC):
    class Fields(BaseFields):
        pass

    description = None

    def __getattr__(self, name):
        if name in [key for key, _ in self.Fields.fields]:
            return self.data[name]
        return object.__getattribute__(self, name)

    def __init__(self, description: str = ''):
        super().__init__()
        self.description = description
        self._data = None

    @cached_property
    def size(self):
        return sum(f.size for (_, f) in self.Fields.fields)

    @cached_property
    def min_size(self):
        return sum(f.min_size for (_, f) in self.Fields.fields)

    @cached_property
    def max_size(self):
        return sum(f.max_size for (_, f) in self.Fields.fields)

    @cached_property
    def data(self):
        if self._data is None:
            raise Exception("Resource wasn't read yet")
        return self._data

    @final
    def read(self, buffer: [BufferedReader, BytesIO], size: int):
        if self._data is not None:
            raise Exception('Block was already read')
        self._data = super().read(buffer, size)
        return self._data

    def _read_internal(self, buffer, size):
        fields = self.Fields.fields
        res = dict()
        for name, field in fields:
            res[name] = field.read(buffer, size)
            size -= field.size
        return res

    @final
    def write(self, buffer, data=None):
        if data is None:
            data = self.data
        super().write(buffer, data)

    def _write_internal(self, buffer, value):
        super()._write_internal(buffer, value)
        fields = self.Fields.fields
        for name, field in fields:
            field.write(buffer, value[name])
