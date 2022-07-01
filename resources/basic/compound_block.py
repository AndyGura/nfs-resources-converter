from abc import ABC
from copy import deepcopy
from functools import cached_property
from io import BufferedReader, BytesIO
from typing import List, Tuple

from resources.basic.data_wrapper import DataWrapper
from resources.basic.exceptions import EndOfBufferException, BlockIntegrityException
from resources.basic.read_block import ReadBlock


class CompoundBlockFields(ABC):
    @classmethod
    @property
    def fields(cls) -> List[Tuple[str, ReadBlock]]:
        try:
            return cls.__fields_cache
        except AttributeError:
            cls.__fields_cache = [(key, value) for (key, value) in cls.__dict__.items() if isinstance(value, ReadBlock)]
            return cls.__fields_cache

    optional_fields: List[str] = []


class CompoundBlock(ReadBlock, ABC):
    class Fields(CompoundBlockFields):
        pass

    def __init__(self, inline_description=False, **kwargs):
        kwargs['inline_description'] = inline_description
        super().__init__(**kwargs)
        self.inline_description = inline_description
        self.instance_fields = [(name, deepcopy(instance)) for name, instance in self.__class__.Fields.fields]
        self.instance_fields_map = {name: res for (name, res) in self.instance_fields}
        self.persistent_data = None

    def __getattr__(self, name):
        if self.instance_fields_map.get(name):
            if isinstance(self.instance_fields_map[name], CompoundBlock):
                return self.instance_fields_map[name]
            else:
                return getattr(self.persistent_data, name, None)
        return object.__getattribute__(self, name)

    @cached_property
    def size(self):
        return sum(f.size for (_, f) in self.instance_fields)

    @cached_property
    def min_size(self):
        return sum(0 if k in self.Fields.optional_fields else f.min_size for (k, f) in self.instance_fields)

    @cached_property
    def max_size(self):
        return sum(f.max_size for (_, f) in self.instance_fields)

    def load_value(self, buffer: [BufferedReader, BytesIO], size: int, parent_read_data: dict = None):
        fields = self.instance_fields
        res = dict()
        remaining_size = size
        for name, field in fields:
            start = buffer.tell()
            if remaining_size == 0:
                if name in self.Fields.optional_fields or field.min_size == 0:
                    continue
                else:
                    raise EndOfBufferException()
            try:
                res[name] = field.read(buffer, remaining_size, parent_read_data=res)
                remaining_size -= buffer.tell() - start
                if remaining_size < 0:
                    raise EndOfBufferException()
            except (EndOfBufferException, BlockIntegrityException) as ex:
                if name in self.Fields.optional_fields:
                    buffer.seek(start)
                else:
                    raise ex
            if hasattr(self, f'_after_{name}_read'):
                getattr(self, f'_after_{name}_read')(data=res,
                                                     buffer=buffer,
                                                     total_size=size,
                                                     remaining_size=remaining_size,
                                                     parent_read_data=parent_read_data)
        return res

    def from_raw_value(self, raw: dict):
        self.persistent_data = DataWrapper(raw)
        return self.persistent_data

    def to_raw_value(self, value: DataWrapper) -> dict:
        return dict(value)


