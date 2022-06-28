class EndOfBufferException(Exception):
    def __init__(self, message='Block read went out of available size'):
        super().__init__(message)


class BlockIntegrityException(Exception):
    def __init__(self, message='Block read went out of available size'):
        super().__init__(message)


class BlockDefinitionException(Exception):
    pass


class MultiReadUnavailableException(Exception):
    def __init__(self, message='Multi-read cannot be done for this read block'):
        super().__init__(message)


class SerializationException(Exception):
    pass
