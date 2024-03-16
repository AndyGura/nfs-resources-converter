def convert_bytes(data):
    if isinstance(data, bytes):
        return list(data)
    elif isinstance(data, dict):
        return {key: convert_bytes(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [convert_bytes(item) for item in data]
    else:
        return data

def serialize_exceptions(data):
    if isinstance(data, Exception):
        return {
            'error_class': data.__class__.__name__,
            'error_text': str(data),
        }
    elif isinstance(data, dict):
        return {key: serialize_exceptions(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [serialize_exceptions(item) for item in data]
    else:
        return data
