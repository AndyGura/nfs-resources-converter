from abc import ABC, abstractmethod
from typing import List, Tuple

from resources.fields import ResourceField, ReadBlock


class BaseFields(ABC):
    @classmethod
    @property
    def fields(cls) -> List[Tuple[str, ResourceField]]:
        return [(key, value) for (key, value) in cls.__dict__.items() if isinstance(value, ResourceField)]


class BaseResource(ReadBlock, ABC):
    class Fields(BaseFields):
        pass

    description = None

    def __init__(self, description: str = ''):
        super().__init__()
        self.description = description

    def __getattr__(self, name):
        if name in [key for key, _ in self.Fields.fields]:
            return self.data[name]
        return object.__getattribute__(self, name)

    @property
    def size(self):
        return sum(f.size for (_, f) in self.Fields.fields)

    @property
    def min_size(self):
        return sum(f.min_size for (_, f) in self.Fields.fields)

    @property
    def max_size(self):
        return sum(f.max_size for (_, f) in self.Fields.fields)

    def _read_internal(self, buffer, size):
        fields = self.Fields.fields
        res = dict()
        for name, field in fields:
            res[name] = field.read(buffer, size)
            size -= field.size
        return res

    def write(self, buffer, value):
        super().write(buffer, value)
        fields = self.Fields.fields
        for name, field in fields:
            field.write(buffer, value[name])


