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
        # TODO should not copy non-persistent fields, where we return pure value (Atomic blocks?)
        self.instance_fields = [(name, deepcopy(instance)) for name, instance in self.__class__.Fields.fields]
        self.instance_fields_map = {name: res for (name, res) in self.instance_fields}
        self.persistent_data = None
        self.initial_buffer_pointer = 0

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        self._id = value
        for (name, field) in self.instance_fields:
            field.id = self._id + ('/' if '__' in self._id else '__') + name

    def __getattr__(self, name):
        if self.instance_fields_map.get(name):
            return getattr(self.persistent_data, name, None)
        return object.__getattribute__(self, name)

    # override conversion of this class to dict
    def __iter__(self):
        yield from self.persistent_data.items() if self.persistent_data else None

    @cached_property
    def size(self):
        try:
            return sum(f.size for (_, f) in self.instance_fields)
        except TypeError:
            return None

    @cached_property
    def min_size(self):
        try:
            return sum(0 if k in self.Fields.optional_fields else f.min_size for (k, f) in self.instance_fields)
        except TypeError:
            return None

    @cached_property
    def max_size(self):
        try:
            return sum(f.max_size for (_, f) in self.instance_fields)
        except TypeError:
            return None

    def load_value(self, buffer: [BufferedReader, BytesIO], size: int, parent_read_data: dict = None):
        self.initial_buffer_pointer = buffer.tell()
        fields = self.instance_fields
        res = dict()
        remaining_size = size
        for name, field in fields:
            if hasattr(self, f'_before_{name}_read'):
                getattr(self, f'_before_{name}_read')(data=res,
                                                      buffer=buffer,
                                                      total_size=size,
                                                      remaining_size=remaining_size,
                                                      parent_read_data=parent_read_data)
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
            except (EndOfBufferException, BlockIntegrityException, NotImplementedError) as ex:
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
        # need to return self, because we want shpi.children.!pal to be instance of BitmapBlock, not dict

        # TODO probably can remove clone here: parent reader should take care of copying instances. For instance, this
        # class is always copying fields on __init__. Arrays should do the same, literal should copy selected block
        # this particular thing slows down TR1.TRI file reading more than twice! 1.55 < 3.35 seconds

        clone = deepcopy(self)
        clone.persistent_data = self.persistent_data
        clone.id = self.id
        return clone

    def to_raw_value(self, value: DataWrapper) -> dict:
        return dict(value)
