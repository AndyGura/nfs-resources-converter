def join_id(base_id: str, *suffix_ids):
    res = base_id
    for i, suff in enumerate(suffix_ids):
        if i > 0 or '__' in base_id:
            res += '/' + suff
        else:
            res += '__' + suff
    return res
