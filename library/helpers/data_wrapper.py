from collections.abc import Iterable
from copy import deepcopy


class DataWrapper(dict):
    MARKER = object()

    @staticmethod
    def wrap(value):
        if isinstance(value, list):
            return [DataWrapper.wrap(x) for x in value]
        elif isinstance(value, dict):
            return DataWrapper(value)
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
        return DataWrapper(deepcopy(dict(self)))

    def __setitem__(self, key, value):
        if isinstance(value, dict) and not isinstance(value, DataWrapper):
            value = DataWrapper(value)
        super(DataWrapper, self).__setitem__(key, value)

    def __getitem__(self, key):
        return self.get(key, None)

    def to_dict(self, serialize_block=False):
        res = dict()
        for key, value in self.items():
            from library.read_data import ReadData
            if isinstance(value, ReadData):
                value = value.value if not serialize_block else value.serialize()
            if isinstance(value, DataWrapper):
                res[key] = value.to_dict()
            elif isinstance(value, list):
                res[key] = [x.to_dict()
                            if isinstance(x, DataWrapper)
                            else dict(x) if isinstance(x, Iterable) else x
                            for x in [v if not isinstance(v, ReadData) else v.value for v in value]]
            elif isinstance(value, Iterable) and not isinstance(value, str):
                res[key] = dict(value)
            else:
                res[key] = value
        return res

    __setattr__, __getattr__ = __setitem__, __getitem__
