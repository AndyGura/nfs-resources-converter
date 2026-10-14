import math

from library.lazy import unloaded_items

# marks an unloaded lazy part in data rendered for the frontend: the dict holds only the seeded values, the frontend
# asks `load_lazy_part` for the rest when it needs it
LAZY_MARKER = '__lazy__'


def convert_bytes(data):
    if isinstance(data, bytes):
        return {'$bytes': list(data)}
    elif isinstance(data, dict):
        items = unloaded_items(data)
        if items is not None:
            return {**{key: convert_bytes(value) for key, value in items}, LAZY_MARKER: True}
        return {key: convert_bytes(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [convert_bytes(item) for item in data]
    elif isinstance(data, float) and math.isnan(data):
        return 'NaN'
    else:
        return data


def revert_bytes(data):
    if isinstance(data, dict):
        if '$bytes' in data and len(data) == 1:
            return bytes(data['$bytes'])
        return {key: revert_bytes(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [revert_bytes(item) for item in data]
    else:
        return data


def serialize_exceptions(data):
    if isinstance(data, Exception):
        return {
            'error_class': data.__class__.__name__,
            'error_text': str(data),
        }
    elif isinstance(data, dict):
        if unloaded_items(data) is not None:
            # an unloaded part holds no exceptions (they come from parsing); kept as is, `convert_bytes` marks it
            return data
        return {key: serialize_exceptions(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [serialize_exceptions(item) for item in data]
    else:
        return data
