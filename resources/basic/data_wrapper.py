from collections.abc import Iterable
from copy import deepcopy


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

    def __deepcopy__(self, memodict={}):
        return DataWrapper(deepcopy(dict(self)))

    def __setitem__(self, key, value):
        if isinstance(value, dict) and not isinstance(value, DataWrapper):
            value = DataWrapper(value)
        super(DataWrapper, self).__setitem__(key, value)

    def __getitem__(self, key):
        return self.get(key, None)

    def to_dict(self):
        res = dict(self)
        for key, value in res.items():
            if isinstance(value, DataWrapper):
                res[key] = value.to_dict()
            elif isinstance(value, Iterable):
                res[key] = dict(value)
            elif isinstance(value, list):
                res[key] = [x.to_dict()
                            if isinstance(x, DataWrapper)
                            else dict(x) if isinstance(x, Iterable) else x
                            for x in value]
        return res

    __setattr__, __getattr__ = __setitem__, __getitem__
