from copy import deepcopy
from io import BufferedReader, BytesIO
from math import floor
from typing import List, Literal

from resources.basic.atomic import AtomicReadBlock
from resources.basic.exceptions import EndOfBufferException, MultiReadUnavailableException, BlockDefinitionException
from resources.basic.read_block import ReadBlock


class ArrayField(ReadBlock):
    child = None

    @property
    def size(self):
        if self.length is None:
            return None
        return self.child.size * self.length

    @property
    def min_size(self):
        if self.length is None:
            return 0
        if self.length_strategy == "strict":
            if not self.child or self.child.min_size is None:
                return None
            return self.child.min_size * self.length
        else:
            return 0

    @property
    def max_size(self):
        if self.length is None:
            return float('inf')
        return self.child.max_size * self.length

    @property
    def length(self):
        return self._length

    @length.setter
    def length(self, value):
        self._length = value

    def __init__(self,
                 child: ReadBlock,
                 length: int = None,
                 length_strategy: Literal["strict", "read_available"] = "strict",
                 length_label: str = None,
                 **kwargs):
        super().__init__(child=child,
                         length=length,
                         length_strategy=length_strategy,
                         length_label=length_label,
                         **kwargs)
        self.child = child
        self._length = length
        self.length_strategy = length_strategy
        if length_label is None:
            if self.length is None:
                length_label = '?'
            elif self.length_strategy == "read_available":
                length_label = f'0..{self.length}'
            else:
                length_label = str(self.length)
        self.length_label = length_label
        self.block_description = f'Array of {length_label} items'

    def from_raw_value(self, raw: List):
        return raw

    def to_raw_value(self, value: List):
        return value

    def load_value(self, buffer: [BufferedReader, BytesIO], size: int, parent_read_data: dict = None):
        res = []
        amount = self.length
        if self.length is None and self.length_strategy != "read_available":
            raise BlockDefinitionException('Array field length is unknown')
        if self.length_strategy == "read_available":
            amount = (min(amount, floor(size / self.child.size))
                      if amount is not None
                      else floor(size / self.child.size))
        start = buffer.tell()
        try:
            if isinstance(self.child, AtomicReadBlock):
                res = self.child.read_multiple(buffer, size, amount, parent_read_data)
                size -= (buffer.tell() - start)
            else:
                raise MultiReadUnavailableException('Supports only atomic read blocks')
        except (MultiReadUnavailableException, AttributeError) as ex:
            buffer.seek(start)
            for i in range(amount):
                start = buffer.tell()
                try:
                    self.child.id = self.id + '/' + str(i)
                    res.append(self.child.read(buffer, size))
                except EndOfBufferException as ex:
                    if self.length_strategy == "read_available":
                        # assume this array is finished
                        buffer.seek(start)
                        return res
                    else:
                        raise ex
                size -= (buffer.tell() - start)
        return res


class ExplicitOffsetsArrayField(ArrayField):

    @property
    def length(self):
        return None if self.offsets is None else len(self.offsets)

    def __init__(self, **kwargs):
        self.offsets = None
        self.lengths = []
        super().__init__(**kwargs)
        self.block_description += ' with custom offset to items'

    def get_item_length(self, item_index, end_offset):
        try:
            return self.lengths[item_index]
        except IndexError:
            pass
        offset = self.offsets[item_index]
        return min(o for o in (self.offsets + [end_offset]) if o > offset) - offset

    def load_value(self, buffer: [BufferedReader, BytesIO], size: int, parent_read_data: dict = None):
        res = []
        if self.offsets is None:
            raise BlockDefinitionException('Explicit offsets array field needs declaration of offsets')
        child_field_instances = [deepcopy(self.child) for _ in self.offsets]
        end_offset = buffer.tell() + size
        for i, offset in enumerate(self.offsets):
            buffer.seek(offset)
            child_field_instances[i].id = self.id + '/' + str(i)
            res.append(child_field_instances[i].read(buffer,
                                                     self.get_item_length(i, end_offset),
                                                     parent_read_data=parent_read_data))
        return res
