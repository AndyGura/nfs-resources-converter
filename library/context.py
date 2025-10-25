from io import BytesIO, BufferedReader


class BaseContext:
    @property
    def ctx_path(self):
        return (self.parent.ctx_path + '/' if self.parent else '') + self.name

    def __init__(self, name: str = '', data=None, block=None, parent=None):
        self.name = name
        self._data = data
        self.block = block
        self.parent = parent
        self.children = {}
        if self.parent:
            self.parent.children[name] = self

    def get_or_create_child(self, name: str, block=None):
        raise NotImplementedError

    def get_full_data(self):
        return self._data

    def child(self, local_path: str):
        path = local_path.split('/')
        ctx = self
        for p in path:
            ctx = ctx.get_or_create_child(p)
            if ctx is None:
                raise Exception(f'Cannot find child "{p}" in context "{self.ctx_path}"')
        return ctx

    def data(self, local_path: str):
        data_path = local_path.split('/')
        entry = self._data
        for p in data_path:
            if entry is None:
                return None
            if p == '..':
                return self.parent.data('/'.join(data_path[1:]))
            if isinstance(entry, list):
                try:
                    entry = entry[int(p)]
                except IndexError:
                    return None
            elif isinstance(entry, dict) and p in entry.keys():
                entry = entry[p]
            elif self.children.get(p):
                return self.children.get(p)._data
            else:
                return None
        return entry

    def relative_block(self, local_path: str):
        block_path = local_path.split('/')
        entry = self.block
        for p in block_path:
            if entry is None:
                return None
            if p == '..':
                return self.parent.relative_block('/'.join(block_path[1:]))
            entry = entry.get_child_block(p)
        return entry


class ReadContext(BaseContext):

    @property
    def local_buffer_pos(self):
        return self.buffer.tell() - self.read_start_offset

    @property
    def read_bytes_remaining(self):
        return self.read_bytes_amount - self.local_buffer_pos

    def get_or_create_child(self, name, block=None, read_bytes_amount=None, data=None):
        existing_child = self.children.get(name)
        if existing_child:
            if block is not None:
                existing_child.block = block
            if read_bytes_amount is not None:
                existing_child.read_bytes_amount = read_bytes_amount
            return existing_child
        return ReadContext(buffer=self.buffer,
                           data=data if data is not None else self.data(name),
                           name=name,
                           block=block or self.relative_block(name),
                           parent=self,
                           read_bytes_amount=read_bytes_amount)

    def __init__(self, buffer: [BufferedReader, BytesIO] = None, name: str = '', data=None, block=None, parent=None,
                 read_bytes_amount=None):
        super().__init__(name=name, data=data, block=block, parent=parent)
        self.buffer = buffer
        self.read_start_offset = buffer.tell() if buffer is not None else None
        self.read_bytes_amount = read_bytes_amount


class WriteContext(BaseContext):

    def get_or_create_child(self, name: str, block=None):
        existing_child = self.children.get('name')
        if existing_child:
            if block is not None:
                existing_child.block = block
            return existing_child
        return WriteContext(result=self.result,
                            name=name,
                            data=self.data(name),
                            block=block or self.relative_block(name),
                            parent=self)

    def __init__(self, result: bytes = b'', name: str = '', data=None, block=None, parent=None):
        super().__init__(name=name, data=data, block=block, parent=parent)
        self.result = result
        self.write_start_offset = len(result)


class DocumentationCtxData:
    def __init__(self, label):
        self.label = label

    def __str__(self):
        return self.label

    def __add__(self, other):
        a = str(self)
        b = str(other)
        return DocumentationCtxData(f'{a}+{b}')

    def __radd__(self, other):
        a = str(other)
        b = str(self)
        return DocumentationCtxData(f'{a}+{b}')

    def __sub__(self, other):
        a = str(self)
        b = str(other)
        return DocumentationCtxData(f'{a}-{b}')

    def __rsub__(self, other):
        a = str(other)
        b = str(self)
        return DocumentationCtxData(f'{a}-{b}')

    def __mul__(self, other):
        a = str(self)
        b = str(other)
        if '+' in a or '-' in a:
            a = f'({a})'
        if '+' in b or '-' in b:
            b = f'({b})'
        return DocumentationCtxData(f'{a}*{b}')

    def __rmul__(self, other):
        a = str(other)
        b = str(self)
        if '+' in a or '-' in a:
            a = f'({a})'
        if '+' in b or '-' in b:
            b = f'({b})'
        return DocumentationCtxData(f'{a}*{b}')


class DocumentationContext(BaseContext):

    @property
    def read_bytes_remaining(self):
        return 'up to end of block'

    @property
    def local_buffer_pos(self):
        return 'local_offset'

    def get_or_create_child(self, name: str, block=None):
        existing_child = self.children.get('name')
        if existing_child:
            if block is not None:
                existing_child.block = block
            return existing_child
        return DocumentationContext(name=name,
                                    data=self.data(name),
                                    block=block or self.relative_block(name),
                                    parent=self)

    def data(self, local_path: str):
        return DocumentationCtxData(local_path.replace('../', '^'))
