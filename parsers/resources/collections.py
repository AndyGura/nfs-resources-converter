import os
from abc import ABC, abstractmethod
from io import BufferedReader
from typing import List, Dict

from parsers.resources.base import BaseResource
from utils import format_exception


class ResourceCollection(BaseResource, ABC):

    def get_resource_by_name(self, name: str) -> BaseResource:
        for resource in self.resources:
            if resource.name == name:
                return resource
        return None

    def __init__(self):
        super().__init__()
        self.resources = []
        self.skipped_resources = []

    def save_converted(self, path: str):
        super().save_converted(path)
        if path[-1] != '/':
            path = path + '/'
        if not os.path.exists(path):
            os.makedirs(path)
        for resource in self.resources:
            print(f'SAVING {self.name}/{resource.name}')
            try:
                resource.save_converted(os.path.join(path, resource.name.replace('/', '_')))
            except BaseException as ex:
                self.skipped_resources.append((resource.name, format_exception(ex)))
        if self.skipped_resources:
            with open(f'{path}/skipped.txt', 'w') as f:
                for item in self.skipped_resources:
                    f.write("%s\t\t%s\n" % item)


class ArchiveResource(ResourceCollection):

    @abstractmethod
    def get_children_descriptors(self, buffer: BufferedReader, length: int) -> List[Dict]:
        pass

    def read(self, buffer: BufferedReader, length: int, path: str = None) -> int:
        super().read(buffer, length, path)
        start_offset = buffer.tell()
        self.resources = []
        self.children_descriptors = self.get_children_descriptors(buffer, length)
        for child in self.children_descriptors:
            from guess_parser import get_resource_class
            buffer.seek(start_offset + child['start_offset'])
            try:
                resource = get_resource_class(buffer)
            except BaseException as ex:
                self.skipped_resources.append((child['name'], format_exception(ex)))
                continue
            resource.name = child['name']
            resource.parent = self
            try:
                print(f'READING {self.name}/{resource.name}')
                bytes_used = resource.read(buffer, child['length'])
                assert bytes_used == child[
                    'length'], f'Bytes used: {bytes_used}, but expected child length: {child["length"]}'
            except BaseException as ex:
                self.skipped_resources.append((child['name'], format_exception(ex)))
                continue
            self.resources.append(resource)
        return length
