import math
import os
from abc import ABC, abstractmethod
from io import BufferedReader
from typing import List, Dict

from parsers.resources.base import BaseResource


class ResourceCollection(BaseResource, ABC):

    def __init__(self):
        super().__init__()
        self.resources = []
        self.skipped_resources = []

    def save_converted(self, path: str):
        if path[-1] != '/':
            path = path + '/'
        if not os.path.exists(path):
            os.makedirs(path)
        for resource in self.resources:
            print(f'SAVING {self.name}/{resource.name}')
            try:
                resource.save_converted(os.path.join(path, resource.name.replace('/', '_')))
            except BaseException as ex:
                self.skipped_resources.append((resource.name, str(ex)))
        if self.skipped_resources:
            with open(f'{path}/skipped.txt', 'w') as f:
                for item in self.skipped_resources:
                    f.write("%s\t\t%s\n" % item)


class ResourceDirectory(ResourceCollection):

    def read(self, path: str, files: List):
        self.name = path
        self.resources = []
        self.skipped_resources = []
        for file in files:
            file_path = os.path.join(path, file)
            with open(file_path, 'rb') as bdata:
                try:
                    from guess_parser import get_resource_class
                    resource = get_resource_class(bdata, file)
                except NotImplementedError as ex:
                    self.skipped_resources.append((file, str(ex)))
                    continue
                resource.name = file
                resource.parent = self
                try:
                    resource.read(bdata, os.path.getsize(file_path), file_path)
                    self.resources.append(resource)
                except BaseException as ex:
                    self.skipped_resources.append((file, str(ex)))
                    continue
        return None


class ArchiveResource(ResourceCollection):

    @abstractmethod
    def get_children_descriptors(self, buffer: BufferedReader, length: int) -> List[Dict]:
        pass

    def read(self, buffer: BufferedReader, length: int, path: str = None) -> int:
        start_offset = buffer.tell()
        self.resources = []
        children_descriptors = self.get_children_descriptors(buffer, length)
        for child in children_descriptors:
            from guess_parser import get_resource_class
            buffer.seek(start_offset + child['start_offset'])
            try:
                resource = get_resource_class(buffer)
            except BaseException as ex:
                self.skipped_resources.append((child['name'], str(ex)))
                continue
            resource.name = child['name']
            resource.parent = self
            try:
                print(f'READING {self.name}/{resource.name}')
                bytes_used = resource.read(buffer, child['length'])
                bytes_used = math.ceil(bytes_used/4)*4
            except BaseException as ex:
                self.skipped_resources.append((child['name'], str(ex)))
                continue
            self.resources.append(resource)
            sub_resources_count = 0
            while bytes_used < child['length']:
                try:
                    sub_resource = get_resource_class(buffer)
                except BaseException as ex:
                    self.skipped_resources.append((f'{resource.name}/{sub_resources_count}', str(ex)))
                    break
                sub_resource.name = str(sub_resources_count)
                sub_resource.parent = resource
                bytes_used = bytes_used + sub_resource.read(buffer, child['length'] - bytes_used)
                resource.resources.append(sub_resource)
                sub_resources_count = sub_resources_count + 1
        return length
