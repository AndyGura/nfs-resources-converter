from abc import ABC
from functools import cached_property
from io import BufferedReader, BytesIO
from typing import List, Tuple, final

from exceptions import ResourceWasntReadException, ResourceAlreadyReadException, EndOfBufferException, \
    BlockIntegrityException
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
        if self.instance_fields_map.get(name):
            if isinstance(self.instance_fields_map[name], BaseResource):
                return self.instance_fields_map[name]
            else:
                return self.data[name]
        return object.__getattribute__(self, name)

    def __init__(self, description: str = '', is_optional=False, **kwargs):
        super().__init__(description=description,
                         is_optional=is_optional,
                         **kwargs)
        self.description = description
        self.is_optional = is_optional
        self.instance_fields = [(name, instance.__class__(**instance.instantiate_kwargs)) for name, instance in self.__class__.Fields.fields]
        self.instance_fields_map = {name: res for (name, res) in self.instance_fields}
        self._data = None

    @cached_property
    def size(self):
        return sum(f.size for (_, f) in self.instance_fields)

    @cached_property
    def min_size(self):
        return sum(0 if getattr(f, 'is_optional', False) else f.min_size for (_, f) in self.instance_fields)

    @cached_property
    def max_size(self):
        return sum(f.max_size for (_, f) in self.instance_fields)

    @cached_property
    def data(self):
        if self._data is None:
            raise ResourceWasntReadException()
        return self._data

    @final
    def read(self, buffer: [BufferedReader, BytesIO], size: int, parent_read_data: dict = None):
        if self._data is not None:
            raise ResourceAlreadyReadException()
        self._data = super().read(buffer, size, parent_read_data)
        return self._data

    def _read_internal(self, buffer, size, parent_read_data: dict = None):
        fields = self.instance_fields
        res = dict()
        remaining_size = size
        for name, field in fields:
            start = buffer.tell()
            if remaining_size == 0:
                if field.is_optional or field.min_size == 0:
                    continue
                else:
                    raise EndOfBufferException()
            try:
                res[name] = field.read(buffer, remaining_size, parent_read_data=res)
            except (EndOfBufferException, BlockIntegrityException) as ex:
                if field.is_optional:
                    buffer.seek(start)
                else:
                    raise ex
            if hasattr(self, f'_after_{name}_read'):
                getattr(self, f'_after_{name}_read')(data=res,
                                                     buffer=buffer,
                                                     total_size=size,
                                                     remaining_size=remaining_size,
                                                     parent_read_data=parent_read_data)
            remaining_size -= buffer.tell() - start
            if remaining_size < 0:
                raise EndOfBufferException()
        return res

    @final
    def write(self, buffer, data=None):
        if data is None:
            data = self.data
        super().write(buffer, data)

    def _write_internal(self, buffer, value):
        super()._write_internal(buffer, value)
        fields = self.instance_fields
        for name, field in fields:
            field.write(buffer, value[name])


class LiteralResource(BaseResource):
    class Fields(BaseFields):
        pass

    @cached_property
    def size(self):
        return self.selected_resource.size if self.selected_resource is not None else None

    @cached_property
    def min_size(self):
        return 0 if self.is_optional else min(x.min_size for x in self.possible_resources)

    @cached_property
    def max_size(self):
        return max(x.max_size for x in self.possible_resources)

    @cached_property
    def data(self):
        return self.selected_resource.data

    def __init__(self, possible_resources: List[BaseResource], **kwargs):
        super().__init__(possible_resources=possible_resources,
                         **kwargs)
        self.possible_resources = [res.__class__(**res.instantiate_kwargs) for res in possible_resources]
        self.selected_resource = None

    def __getattr__(self, name):
        if self.selected_resource and self.selected_resource.instance_fields_map.get(name):
            return getattr(self.selected_resource, name)
        return super().__getattr__(name)

    def _read_internal(self, buffer, size, parent_read_data: dict = None):
        from guess_parser import probe_block_class
        block_class = probe_block_class(buffer, resources_to_pick=[x.__class__ for x in self.possible_resources])
        if not block_class:
            raise BlockIntegrityException('Expectation failed for literal block: class not found')
        selected_resource = None
        for res in self.possible_resources:
            if isinstance(res, block_class):
                selected_resource = res
                break
        result = selected_resource.read(buffer, size)
        self.selected_resource = selected_resource
        return result

    def _write_internal(self, buffer, value):
        self.selected_resource._write_internal(buffer, value)
