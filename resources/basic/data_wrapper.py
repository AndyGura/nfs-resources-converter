class DataWrapper(dict):
    MARKER = object()

    def __init__(self, value: dict = None):
        if value is None:
            pass
        elif isinstance(value, dict):
            for key in value:
                self.__setitem__(key, value[key])
        else:
            raise TypeError('expected dict')

    def __setitem__(self, key, value):
        if isinstance(value, dict) and not isinstance(value, DataWrapper):
            value = DataWrapper(value)
        super(DataWrapper, self).__setitem__(key, value)

    def __getitem__(self, key):
        return self.get(key, None)

    __setattr__, __getattr__ = __setitem__, __getitem__
