from io import BufferedReader, BytesIO
from math import floor
from typing import List, Literal

from library.helpers.exceptions import BlockDefinitionException, MultiReadUnavailableException, EndOfBufferException, \
    SerializationException
from library.helpers.id import join_id
from library.read_blocks.atomic import AtomicReadBlock
from library.read_blocks.read_block import ReadBlock


class ArrayBlock(ReadBlock):
    child = None

    def get_size(self, state):
        length = self.get_length(state)
        if length is None:
            return None
        return sum(self.child.get_size(state.get('children_states', {}).get(str(i), {})) for i in range(length))

    def get_min_size(self, state):
        length = self.get_length(state)
        if length is None:
            return 0
        if self.length_strategy == "strict":
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
        return sum(self.child.get_max_size(state.get('children_states', {}).get(str(i), {})) for i in range(length))

    def get_length(self, state):
        return self._length if self._length is not None else state.get('length')

    def __init__(self,
                 child: ReadBlock,
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

    def to_raw_value(self, data: List, state) -> bytes:
        res = bytes()
        for item in data:
            if isinstance(item, Exception):
                raise SerializationException('Cannot serialize block with errors')
            res += self.child.to_raw_value(item, item.block_state)
        if self.length and self.length > len(data) and self.length_strategy != 'read_available':
            res += bytes([0] * (self.length - len(data)) * self.child.size)
        return res

    def _load_value(self, buffer: [BufferedReader, BytesIO], size: int, state: dict, parent_read_data: dict = None):
        res = []
        amount = self.get_length(state)
        if amount is None and self.length_strategy != "read_available":
            raise BlockDefinitionException('Array field length is unknown')
        if self.length_strategy == "read_available":
            if isinstance(self.child, AtomicReadBlock):
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
        if not state.get('children_states'):
            state['children_states'] = { str(i): {'id': join_id(state.get('id'), str(i)),
                                                  **state.get('common_children_states', {})} for i in range(amount) }
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
                    if not state['children_states'][str(i)]:
                        state['children_states'][str(i)] = {'id': join_id(state.get('id'), str(i))}
                    res.append(self.child.read(buffer, size, {
                        **state.get('common_children_states', {}),
                        **state['children_states'][str(i)]
                    }))
                except EndOfBufferException as ex:
                    if self.length_strategy == "read_available":
                        # assume this array is finished
                        buffer.seek(start)
                        return res
                    else:
                        raise ex
                size -= (buffer.tell() - start)
        return res


# TODO probably not needed anymore. it is the array of detached blocks
class ExplicitOffsetsArrayBlock(ArrayBlock):

    def get_length(self, state):
        base_length = super().get_length(state)
        if base_length is None and state.get('offsets') is not None:
            return len(state.get('offsets'))
        return base_length

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.block_description += ' with custom offset to items'

    def get_item_length(self, state, item_index, end_offset):
        try:
            return state['lengths'][item_index]
        except (KeyError, IndexError):
            pass
        offset = state['offsets'][item_index]
        return min(o for o in (state['offsets'] + [end_offset]) if o > offset) - offset

    def _load_value(self, buffer: [BufferedReader, BytesIO], size: int, state: dict, parent_read_data: dict = None):
        res = []
        if state.get('offsets') is None:
            raise BlockDefinitionException('Explicit offsets array field needs declaration of offsets')
        end_offset = buffer.tell() + size
        custom_names = state.get('custom_names')
        offsets = state.get('offsets', [])
        for i, offset in enumerate(offsets):
            buffer.seek(offset)
            try:
                child_state = state.get('children_states', [])[i]
            except IndexError:
                child_state = {}
            child_state['id'] = join_id(state.get('id'), (str(i) if not custom_names else custom_names[i]))
            res.append(self.child.read(buffer, self.get_item_length(state, i, end_offset), child_state, parent_read_data=parent_read_data))
        return res
