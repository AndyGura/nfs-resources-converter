def join_id(base_id: str, suffix_id: str):
    if '__' in base_id:
        return base_id + '/' + suffix_id
    else:
        return base_id + '__' + suffix_id
