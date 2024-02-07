from collections.abc import Iterable
from copy import deepcopy


class ClassDict(dict):
    MARKER = object()

    @staticmethod
    def wrap(value):
        if isinstance(value, list):
            return [ClassDict.wrap(x) for x in value]
        elif isinstance(value, dict):
            return ClassDict(value)
        return value

    def __init__(self, value: dict = None):
        if value is None:
            pass
        elif isinstance(value, dict):
            for key in value:
                self.__setitem__(key, value[key])
        else:
            raise TypeError('expected dict')

    def __deepcopy__(self, memodict={}):
        return ClassDict(deepcopy(dict(self)))

    def __setitem__(self, key, value):
        if isinstance(value, dict) and not isinstance(value, ClassDict):
            value = ClassDict(value)
        super(ClassDict, self).__setitem__(key, value)

    def __getitem__(self, key):
        return self.get(key, None)

    def to_dict(self):
        res = dict()
        for key, value in self.items():
            if isinstance(value, ClassDict):
                res[key] = value.to_dict()
            elif isinstance(value, bytes):
                res[key] = list(value)
            elif isinstance(value, list):
                res[key] = [x.to_dict()
                            if isinstance(x, ClassDict)
                            else dict(x) if isinstance(x, Iterable) else x
                            for x in value]
            elif isinstance(value, Iterable) and not isinstance(value, str):
                res[key] = dict(value)
            else:
                res[key] = value
        return res

    __setattr__, __getattr__ = __setitem__, __getitem__
