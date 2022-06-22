from abc import ABC

from resources.fields import ResourceField, ReadBlock


class BaseResource(ReadBlock, ABC):
    description = None

    def __init__(self, description: str = ''):
        self.description = description

    @property
    def size(self):
        return sum(f.size for (_, f) in self._fields)

    @property
    def min_size(self):
        return sum(f.min_size for (_, f) in self._fields)

    @property
    def max_size(self):
        return sum(f.max_size for (_, f) in self._fields)

    @property
    def _fields(self):
        return [(key, value) for (key, value) in self.__class__.__dict__.items() if isinstance(value, ResourceField)]

    def read(self, buffer, size):
        super().read(buffer, size)
        fields = self._fields
        res = dict()
        for name, field in fields:
            res[name] = field.read(buffer, size)
            size -= field.size
        return res

    def write(self, buffer, value):
        super().write(buffer, value)
        fields = self._fields
        for name, field in fields:
            field.write(buffer, value[name])


