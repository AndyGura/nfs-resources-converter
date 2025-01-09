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
        self.children = []
        if self.parent:
            self.parent.children.append(self)

    def data(self, local_path: str):
        data_path = local_path.split('/')
        entry = self._data
        for p in data_path:
            if p == '..':
                return self.parent.data('/'.join(data_path[1:]))
            if isinstance(entry, list):
                entry = entry[int(p)]
            else:
                entry = entry[p]
        return entry

    def relative_block(self, local_path: str):
        block_path = local_path.split('/')
        entry = self.block
        for p in block_path:
            if p == '..':
                return self.parent.relative_block('/'.join(block_path[1:]))
            entry = entry.get_child_block(p)
        return entry

    def get_full_data(self):
        return self._data


class ReadContext(BaseContext):

    def __init__(self, buffer: [BufferedReader, BytesIO] = None, name: str = '', data=None, block=None, parent=None,
                 read_bytes_amount=None):
        super().__init__(name=name, data=data, block=block, parent=parent)
        self.buffer = buffer
        self.read_start_offset = buffer.tell() if buffer is not None else None
        self.read_bytes_amount = read_bytes_amount


class WriteContext(BaseContext):
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

    def data(self, local_path: str):
        return DocumentationCtxData(local_path.replace('../', '^'))
