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
        return self.child.min_size * self.length if self.length_strategy == "strict" else 0

    @property
    def max_size(self):
        if self.length is None:
            return float('inf')
        return self.child.max_size * self.length

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
        self.length = length
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
            for _ in range(amount):
                start = buffer.tell()
                try:
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
