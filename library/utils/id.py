from typing import Tuple


def join_id(base_id: str, *suffix_ids):
    res = base_id
    for i, suff in enumerate(suffix_ids):
        if i > 0 or '__' in base_id:
            res += '/' + suff
        else:
            res += '__' + suff
    return res

def split_last_id_part(id: str) -> Tuple[str, str]:
    parts = id.split('/')
    if '__' in parts[-1]:
        suffix_parts = parts[-1].split('__')
        return '/'.join(parts[:-1] + suffix_parts[:-1]), suffix_parts[-1]
    return '/'.join(parts[:-1]), parts[-1]