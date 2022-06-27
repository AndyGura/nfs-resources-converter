class ResourceWasntReadException(Exception):
    def __init__(self, message="Resource wasn't read yet"):
        super().__init__(message)


class ResourceAlreadyReadException(Exception):
    def __init__(self, message='Block was already read'):
        super().__init__(message)


class EndOfBufferException(Exception):
    def __init__(self, message='Block read went out of available size'):
        super().__init__(message)


class BlockIntegrityException(Exception):
    def __init__(self, message='Block read went out of available size'):
        super().__init__(message)


class BlockDefinitionException(Exception):
    pass


class SerializationException(Exception):
    pass
