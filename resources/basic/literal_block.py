from copy import deepcopy
from copy import deepcopy
from io import BufferedReader, BytesIO
from typing import List

from resources.basic.compound_block import CompoundBlock
from resources.basic.exceptions import BlockIntegrityException
from resources.basic.read_block import ReadBlock


class LiteralResource(ReadBlock):
    @property
    def size(self):
        return (self.selected_resource.size
                if self.selected_resource is not None
                else None)

    @property
    def min_size(self):
        return (self.selected_resource.min_size
                if self.selected_resource is not None
                else min(x.min_size for x in self.possible_resources))

    @property
    def max_size(self):
        return (self.selected_resource.max_size
                if self.selected_resource is not None
                else max(x.max_size for x in self.possible_resources))

    @property
    def Fields(self):
        return self.selected_resource.Fields

    def __init__(self, possible_resources: List[CompoundBlock], **kwargs):
        super().__init__(possible_resources=possible_resources,
                         **kwargs)
        self.possible_resources = deepcopy(possible_resources)
        self.selected_resource = None
        self.persistent_data = None

    def __getattr__(self, name):
        if (self.selected_resource
                and isinstance(self.selected_resource, CompoundBlock)
                and self.selected_resource.instance_fields_map.get(name)):
            return getattr(self.persistent_data, name, None)
        return object.__getattribute__(self, name)

    def read(self, buffer: [BufferedReader, BytesIO], size: int, parent_read_data: dict = None):
        if self.selected_resource is None:
            from guess_parser import probe_block_class
            block_class = probe_block_class(buffer, resources_to_pick=[x.__class__ for x in self.possible_resources])
            if not block_class:
                raise BlockIntegrityException('Expectation failed for literal block while reading: class not found')
            for res in self.possible_resources:
                if isinstance(res, block_class):
                    self.selected_resource = res
                    break
        try:
            self.persistent_data = super().read(buffer, size, parent_read_data)
            return self.persistent_data
        finally:
            self.selected_resource = None

    def load_value(self, buffer: [BufferedReader, BytesIO], size: int, parent_read_data: dict = None):
        return self.selected_resource.load_value(buffer, size, parent_read_data)

    def from_raw_value(self, raw: bytes):
        if self.selected_resource is None:
            raise BlockIntegrityException('Expectation failed for literal block while from_raw_value: class not found')
        return self.selected_resource.from_raw_value(raw)

    def to_raw_value(self, value) -> bytes:
        return self.selected_resource.to_raw_value(value)

    def _read_internal(self, buffer, size, parent_read_data: dict = None):
        from guess_parser import probe_block_class
        block_class = probe_block_class(buffer, resources_to_pick=[x.__class__ for x in self.possible_resources])
        if not block_class:
            raise BlockIntegrityException('Expectation failed for literal block while _read_internal: class not found')
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
