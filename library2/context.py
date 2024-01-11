from io import BytesIO, BufferedReader


class Context:
    @property
    def ctx_path(self):
        return (self.parent.ctx_path + '/' if self.parent else '') + self.name

    def __init__(self, buffer: [BufferedReader, BytesIO]=None, name='', data=None, parent=None):
        self.buffer = buffer
        self.name = name
        self._data = data
        self.parent = parent
        self.children = []
        if self.parent:
            self.parent.children.append(self)

    def data(self, local_path: str):
        return self._data[local_path] # TODO support paths, like ../amount
