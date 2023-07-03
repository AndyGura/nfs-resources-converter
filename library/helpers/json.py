from collections import defaultdict
from collections.abc import Iterable

from library.helpers.data_wrapper import DataWrapper


def rec_dd():
    return defaultdict(rec_dd)


def resource_to_json(item):
    from library.read_data import ReadData
    if isinstance(item, ReadData):
        item = item.value
    if isinstance(item, list):
        return [resource_to_json(x) for x in item]
    if isinstance(item, DataWrapper):
        return item.to_dict()
    if isinstance(item, bytes):
        return list(item)
    if isinstance(item, Iterable) and not isinstance(item, str):
        return dict(item)
    return item
