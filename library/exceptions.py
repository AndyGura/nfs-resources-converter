class EndOfBufferException(Exception):
    def __init__(self, message='Block read went out of available size'):
        super().__init__(message)


class DataIntegrityException(Exception):
    def __init__(self, message='Data integrity exception'):
        super().__init__(message)


class BlockDefinitionException(Exception):
    pass


class SerializationException(Exception):
    pass
