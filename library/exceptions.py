class EndOfBufferException(Exception):
    def __init__(self, message='Block read went out of available size'):
        super().__init__(message)


class DataIntegrityException(Exception):
    def __init__(self, message='Data integrity exception'):
        super().__init__(message)


class BlockDefinitionException(Exception):
    def __init__(self, ctx, message):
        if ctx is not None:
            super().__init__(ctx.ctx_path + ': ' + message)
        else:
            super().__init__(message)


class SerializationException(Exception):
    pass
