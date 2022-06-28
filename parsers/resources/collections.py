import json
import os
from abc import ABC, abstractmethod
from io import BufferedReader
from multiprocessing import Pool, cpu_count
from typing import List, Dict

import settings
from parsers.resources.base import BaseResource


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
                self.skipped_resources.append((resource.name, f'{ex.__class__.__name__}: {str(ex)}'))
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
                    self.skipped_resources.append((file, f'{ex.__class__.__name__}: {str(ex)}'))
                    continue
                resource.name = file
                resource.parent = self
                try:
                    resource.read(bdata, os.path.getsize(file_path), file_path)
                    self.resources.append(resource)
                except BaseException as ex:
                    self.skipped_resources.append((file, f'{ex.__class__.__name__}: {str(ex)}'))
                    continue
        self.skipped_resources.sort(key=lambda x:x[0])
        return None


class MultiprocessResourceDirectory(ResourceCollection):

    def _process_file(self, read_path, path, file):
        file_path = os.path.join(read_path, file)
        with open(file_path, 'rb') as bdata:
            try:
                from guess_parser import get_resource_class
                resource = get_resource_class(bdata, file)
                resource.name = file
                resource.parent = self
                resource.read(bdata, os.path.getsize(file_path), file_path)
                self.resources.append(resource)
                print(f'SAVING {self.name}/{resource.name}')
                resource.save_converted(os.path.join(path, resource.name.replace('/', '_')))
                return 0
            except BaseException as ex:
                return file, f'{ex.__class__.__name__}: {str(ex)}'

    def read(self, path: str, files: List):
        self.name = path
        self.read_path = path
        self.files = files
        self.skipped_resources = []
        return None

    def save_converted(self, path: str):
        if self.unknowns and settings.save_unknown_values:
            with open(f'{path}__unknowns.json', 'w') as file:
                file.write(json.dumps(self.unknowns, indent=4))
        self.resources = []
        self.skipped_resources = []
        if path[-1] != '/':
            path = path + '/'
        if not os.path.exists(path):
            os.makedirs(path)
        with Pool(processes=cpu_count()) as pool:
            results = [pool.apply_async(self._process_file, (self.read_path, path, file)) for file in self.files]
            [result.wait() for result in results]
            self.skipped_resources = [res for res in (r.get() for r in results) if res != 0]
            if self.skipped_resources:
                self.skipped_resources.sort(key=lambda x:x[0])
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
                self.skipped_resources.append((child['name'], f'{ex.__class__.__name__}: {str(ex)}'))
                continue
            resource.name = child['name']
            resource.parent = self
            try:
                print(f'READING {self.name}/{resource.name}')
                bytes_used = resource.read(buffer, child['length'])
                assert bytes_used == child['length'], f'Bytes used: {bytes_used}, but expected child length: {child["length"]}'
            except BaseException as ex:
                self.skipped_resources.append((child['name'], f'{ex.__class__.__name__}: {str(ex)}'))
                continue
            self.resources.append(resource)
        return length
