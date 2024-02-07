def convert_bytes(data):
    if isinstance(data, bytes):
        return list(data)
    elif isinstance(data, dict):
        return {key: convert_bytes(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [convert_bytes(item) for item in data]
    else:
        return data
