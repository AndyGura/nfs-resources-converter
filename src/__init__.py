import os

from guess_parser import probe_block_class


# id example: /media/data/nfs/SIMDATA/CARFAMS/LDIABL.CFM__1/frnt
def require_resource(id: str):
    file_path = id.split('__')[0]
    resource = require_file(file_path)
    resource_path = id.split('__')[1].split('/')
    for key in resource_path:
        if isinstance(resource, list) and key.isdigit():
            try:
                resource = resource[int(key)]
                continue
            except KeyError:
                return None
        try:
            resource = getattr(resource, key)
        except AttributeError:
            return None
        if not resource:
            return None
    return resource


# not shared between processes: in most cases if file requires another resource, it is in the same file, or it
# requires one external file multiple times. It will be more time-consuming to serialize/deserialize it for sharing
# between processes than load some file multiple times. + we avoid potential memory leaks
files_cache = {}


def require_file(path: str):
    block = files_cache.get(path)
    if block is None:
        with open(path, 'rb') as bdata:
            block_class = probe_block_class(bdata, path)
            block = block_class()
            block.id = path
            block.read(bdata, os.path.getsize(path))
        files_cache[path] = block
    return block
