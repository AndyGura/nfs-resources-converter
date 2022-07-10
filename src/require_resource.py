import os
import traceback
from multiprocessing import Manager
from time import sleep

from guess_parser import probe_block_class
from resources.basic.data_wrapper import DataWrapper

files_loaded_manager = Manager()
files_loaded_manager.register('DataWrapper', DataWrapper)
files_loaded = files_loaded_manager.dict()


# id example: /media/data/nfs/SIMDATA/CARFAMS/LDIABL.CFM__1/frnt
def require_resource(id: str):
    file_path = id.split('__')[0]
    file = require_file(file_path)
    # TODO
    return file


def require_file(path: str):
    file_path = path.split('__')[0]
    file = files_loaded.get(file_path)
    if file is None:
        files_loaded[file_path] = 'LOADING'
        try:
            with open(path, 'rb') as bdata:
                block_class = probe_block_class(bdata, path)
                block = block_class()
                block.read(bdata, os.path.getsize(path))
                file = block
                # TODO remove setting to file: added for debug
                files_loaded[file_path] = file = (block.__class__, block.instantiate_kwargs, block.persistent_data.to_dict())
        except Exception as ex:
            files_loaded[file_path] = file = ex
    elif file == 'LOADING':
        while files_loaded[file_path] == 'LOADING':
            sleep(0.1)
        file = files_loaded[file_path]
    if isinstance(file, Exception):
        raise file
    if isinstance(file, tuple):
        reconstructed_file = file[0](**file[1])
        reconstructed_file.persistent_data = DataWrapper(file[2])
        file = reconstructed_file
    return file
