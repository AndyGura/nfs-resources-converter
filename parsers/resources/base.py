import json
from abc import ABC, abstractmethod
from io import BufferedReader

import settings


class BaseResource(ABC):
    unknowns = []

    name = None
    parent = None
    read_from_path = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.unknowns = []

    @abstractmethod
    def read(self, buffer: BufferedReader, length: int, path: str = None) -> int:
        self.read_from_path = path
        # returns how many bytes were used
        pass

    def save_converted(self, path: str):
        if self.unknowns and settings.save_unknown_values:
            with open(f'{path}__unknowns.json', 'w') as file:
                file.write(json.dumps(self.unknowns, indent=4))

