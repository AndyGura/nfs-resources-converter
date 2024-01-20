from io import BytesIO, BufferedReader

class BaseContext:
    @property
    def ctx_path(self):
        return (self.parent.ctx_path + '/' if self.parent else '') + self.name

    def __init__(self, name: str='', data=None, block=None, parent=None):
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
        # TODO support paths, like ../amount
        for p in data_path:
            entry = entry[p]
        return entry

    def get_full_data(self):
        return self._data

class ReadContext(BaseContext):

    def __init__(self, buffer: [BufferedReader, BytesIO] = None, name: str='', data=None, block=None, parent=None, read_bytes_amount=None):
        super().__init__(name=name, data=data, block=block, parent=parent)
        self.buffer = buffer
        self.read_start_offset = buffer.tell() if buffer is not None else None
        self.read_bytes_amount = read_bytes_amount


class WriteContext(BaseContext):
    def __init__(self, result: bytes = b'', name: str='', data=None, block=None, parent=None):
        super().__init__(name=name, data=data, block=block, parent=parent)
        self.result = result
        self.write_start_offset = len(result)
