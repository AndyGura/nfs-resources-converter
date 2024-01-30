from io import BufferedReader, BytesIO
from math import floor
from typing import List, Literal

from library.helpers.exceptions import (BlockDefinitionException,
                                        MultiReadUnavailableException,
                                        EndOfBufferException,
                                        SerializationException,
                                        )
from library.helpers.id import join_id
from library.read_blocks.atomic import AtomicDataBlock
from library.read_blocks.data_block import DataBlock
from library.read_data import ReadData


class ArrayBlock(DataBlock):
    child = None

    def get_size(self, state):
        length = self.get_length(state)
        if length is None:
            return None
        if isinstance(self.child, AtomicDataBlock):
            return self.child.static_size * length
        return sum(self.child.get_size(state.get('children_states', {}).get(str(i), {})) for i in range(length))

    def get_min_size(self, state):
        length = self.get_length(state)
        if length is None:
            return 0
        if self.length_strategy == "strict":
            if isinstance(self.child, AtomicDataBlock):
                return self.child.static_size * length
            try:
                return sum(self.child.get_min_size(state.get('children_states', {}).get(str(i), {})) for i in range(length))
            except TypeError:
                return None
        else:
            return 0

    def get_max_size(self, state):
        length = self.get_length(state)
        if length is None:
            return float('inf')
        if isinstance(self.child, AtomicDataBlock):
            return self.child.static_size * length
        return sum(self.child.get_max_size(state.get('children_states', {}).get(str(i), {})) for i in range(length))

    def get_length(self, state):
        return self._length if self._length is not None else state.get('length')

    def __init__(self,
                 child: DataBlock,
                 length: int = None,
                 length_strategy: Literal["strict", "read_available"] = "strict",
                 length_label: str = None,
                 **kwargs):
        super().__init__(**kwargs)
        self.child = child
        self._length = length
        self.length_strategy = length_strategy
        if length_label is None:
            length = self.get_length({})
            if length is None:
                length_label = '?'
            elif self.length_strategy == "read_available":
                length_label = f'0..{length}'
            else:
                length_label = str(length)
        self.length_label = length_label
        self.block_description = f'Array of {length_label} items'

    def from_raw_value(self, raw: List, state: dict):
        return raw

    def to_raw_value(self, data: ReadData) -> bytes:
        res = bytes()
        for item in data:
            if isinstance(item, Exception):
                raise SerializationException('Cannot serialize block with errors')
            res += self.child.to_raw_value(item)
        return res

    def _load_value(self, buffer: [BufferedReader, BytesIO], size: int, state: dict):
        res = []
        amount = self.get_length(state)
        if amount is None and self.length_strategy != "read_available":
            raise BlockDefinitionException('Array field length is unknown')
        if self.length_strategy == "read_available":
            if isinstance(self.child, AtomicDataBlock):
                amount = (min(amount, floor(size / self.child.static_size))
                          if amount is not None
                          else floor(size / self.child.static_size))
            else:
                calculated_amount = 0
                size_left = size
                while (amount is None) or (calculated_amount < amount):
                    child_state = {}
                    try:
                        child_state = state['children_states'][str(calculated_amount)]
                    except:
                        pass
                    size_left -= self.child.get_size(child_state)
                    if size_left < 0:
                        break
                    calculated_amount += 1
                amount = calculated_amount
        id_prefix = join_id(state.get('id'), '')
        if not self.child.simplified and not state.get('children_states'):
            common_states = state.get('common_children_states', {})
            state['children_states'] = {str(i): {'id': id_prefix + str(i), **common_states} for i in range(amount)}
        start = buffer.tell()
        try:
            if isinstance(self.child, AtomicDataBlock):
                res = self.child.read_multiple(buffer, size, [x for x in state.get('children_states', {}).values()], amount)
                size -= (buffer.tell() - start)
            else:
                raise MultiReadUnavailableException('Supports only atomic data blocks')
        except (MultiReadUnavailableException, AttributeError) as ex:
            buffer.seek(start)
            for i in range(amount):
                start = buffer.tell()
                try:
                    if not self.child.simplified and not state['children_states'][str(i)]:
                        state['children_states'][str(i)] = {'id': id_prefix + str(i)}
                    res.append(self.child.read(buffer, size, {
                        **state.get('common_children_states', {}),
                        **state['children_states'][str(i)]
                    } if not self.child.simplified else None))
                except EndOfBufferException as ex:
                    if self.length_strategy == "read_available":
                        # assume this array is finished
                        buffer.seek(start)
                        return res
                    else:
                        raise ex
                size -= (buffer.tell() - start)
        return res
