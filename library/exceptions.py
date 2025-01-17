class ReadWriteException(Exception):
    def __init__(self, message, ctx=None):
        self.ctx_path = ctx.ctx_path if ctx is not None else None
        if self.ctx_path is not None:
            super().__init__('[' + self.ctx_path + '] ' + message)
        else:
            super().__init__(message)


class EndOfBufferException(ReadWriteException):
    def __init__(self, message='Block read went out of available size', **kwargs):
        super().__init__(message, **kwargs)


class DataIntegrityException(ReadWriteException):
    def __init__(self, message='Data integrity exception', **kwargs):
        super().__init__(message, **kwargs)


class BlockDefinitionException(ReadWriteException):
    pass


class SerializationException(Exception):
    pass
