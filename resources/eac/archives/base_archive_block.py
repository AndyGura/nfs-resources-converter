from abc import abstractmethod, ABC
from io import BufferedReader, BytesIO, SEEK_CUR

from library.context import ReadContext, WriteContext
from library.read_blocks import (DeclarativeCompoundBlock,
                                 DataBlock)


### A block, which contains multiple data blocks, consist of header with item descriptions and
### separate space when items themselves located.
###
### Expects implementation to have fields `items_descr` which returns list of descriptions and `children`,
### which describes children.
###
### In returned data, besides `children`, provides additional fields:
### - `offset_payloads` - byte arrays with data, found between children. This list always has length len(children) + 1
### - `children_aliases` - list of strings, identifiers of items. This list always has the same length as children.
### Aliases can repeat
class BaseArchiveBlock(DeclarativeCompoundBlock, ABC):

    def new_data(self):
        # CompoundBlock does not create those custom fields
        return {**super().new_data(),
                'children': [],
                'children_aliases': [],
                'offset_payloads': [b'']}

    ### should transform data['items_descr'] to list of tuples (alias, offset, length)
    @abstractmethod
    def parse_abs_offsets(self, block_start, data, read_bytes_amount):
        raise NotImplementedError

    ### should transform list of tuples (alias, offset, length) to data['items_descr']
    @abstractmethod
    def generate_items_descr(self, data, children):
        raise NotImplementedError

    def handle_archive_child(self, buffer, abs_offsets, i, self_ctx):
        (alias, offset, length) = abs_offsets[i]
        if offset > buffer.tell():
            offset_payload = buffer.read(offset - buffer.tell())
        else:
            offset_payload = b''
            buffer.seek(offset)
        child = self.field_blocks_map['children'].child.unpack(self_ctx.buffer, ctx=self_ctx, name=alias,
                                                               read_bytes_amount=length)
        return [offset_payload], [alias], [child]

    def read(self, buffer: [BufferedReader, BytesIO], ctx: ReadContext = DataBlock.root_read_ctx, name: str = '',
             read_bytes_amount=None):
        block_start = buffer.tell()
        res = super().read(buffer, ctx, name, read_bytes_amount)
        end_pos = buffer.tell()
        buffer.seek(-len(res['data_bytes']), SEEK_CUR)
        self_ctx = next(c for c in ctx.children if c.name == name)
        abs_offsets = self.parse_abs_offsets(block_start, res, read_bytes_amount)
        res['children'] = []
        res['children_aliases'] = []
        res['offset_payloads'] = []
        for i in range(len(abs_offsets)):
            # recursive reference, happens in wwww blocks
            if abs_offsets[i][1] == block_start:
                res['offset_payloads'].append(b'')
                res['children_aliases'].append(None)
                res['children'].append(None)
                continue
            (op, a, c) = self.handle_archive_child(buffer, abs_offsets, i, self_ctx)
            res['offset_payloads'].extend(op)
            res['children_aliases'].extend(a)
            res['children'].extend(c)
        if res.get('length') is not None and buffer.tell() < block_start + res['length']:
            diff = block_start + res['length'] - buffer.tell()
            res['offset_payloads'].append(buffer.read(diff))
        else:
            res['offset_payloads'].append(b'')
        buffer.seek(end_pos)
        return res

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        data['data_bytes'] = b''
        children = []
        child_block = self.field_blocks_map['children'].child
        for i, item in enumerate(data['children']):
            data['data_bytes'] += data['offset_payloads'][i]
            item_data = child_block.pack(data=item, ctx=ctx, name=str(i))
            children.append((data['children_aliases'][i], len(data['data_bytes']), len(item_data)))
            data['data_bytes'] += item_data
        data['data_bytes'] += data['offset_payloads'][-1]
        data['items_descr'] = self.generate_items_descr(data, children)
        return super().write(data=data, ctx=ctx, name=name)
