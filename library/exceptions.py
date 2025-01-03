class ReadWriteException(Exception):
    def __init__(self, message, ctx=None):
        if ctx is not None:
            super().__init__('[' + ctx.ctx_path + '] ' + message)
        else:
            super().__init__(message)
        self.ctx = ctx


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
