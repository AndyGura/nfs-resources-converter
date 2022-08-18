from io import BufferedWriter
from typing import TypeVar, Generic

T = TypeVar('T')


class ReadData(Generic[T]):
    def __init__(self, value, block: T, block_state: dict):
        self.value = value
        self.block = block
        self.block_state = block_state

    def __getattr__(self, item):
        if item not in ['value', 'block', 'block_state']:
            if self.value:
                elem = getattr(self.value, item)
                if elem is not None:
                    return elem
        return object.__getattribute__(self, item)

    def __iter__(self):
        yield from self.value if self.value is not None else []

    def __getitem__(self, key):
        if self.value is None:
            raise KeyError(key)
        return self.value[key]

    def __len__(self):
        return len(self.value)

    def __eq__(self, other):
        return self.value == other

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return f'ReadData <{self.block.__class__.__name__}> {self.id}'

    @property
    def id(self):
        return self.block_state['id']

    def write(self, buffer: BufferedWriter):
        self.block.write(buffer, self)

    def to_bytes(self):
        return self.block.to_raw_value(self)

    def serialize(self):
        return

    def serialize(self):
        from library.helpers.data_wrapper import DataWrapper
        if isinstance(self.value, DataWrapper):
            value = self.value.to_dict(serialize_block=True)
        elif isinstance(self.value, list) and len(self.value) > 0 and isinstance(self.value[0], ReadData):
            value = [x.serialize() for x in self.value]
        else:
            value = self.value
        return {
            'block_class_mro': '__'.join(
                [x.__name__ for x in self.block.__class__.mro() if x.__name__ not in ['object', 'ABC']]),
            'block': self.block.__dict__,
            'block_state': self.block_state,
            'value': value
        }
