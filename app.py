import argparse
import os
import pathlib
import time

import settings
from guess_parser import get_resource_class
from parsers.resources.collections import ResourceDirectory, MultiprocessResourceDirectory

start_time = time.time()

resource = argparse.ArgumentParser()
resource.add_argument('file', type=pathlib.Path)
args = resource.parse_args()

if os.path.isdir(args.file):
    for subdir, dirs, files in os.walk(args.file):
        multiprocess_blacklisted = settings.multiprocess_processes_count == 1
        if not multiprocess_blacklisted:
            for bl in settings.multiprocess_directory_blacklist:
                if subdir.endswith(bl):
                    multiprocess_blacklisted = True
                    break
        res = ResourceDirectory() if multiprocess_blacklisted else MultiprocessResourceDirectory()
        res.read(subdir, files)
        res.save_converted(os.path.join('out', subdir).replace('\\', '/'))
else:
    with args.file.open('rb') as bdata:
        resource = get_resource_class(bdata, bdata.name)
        resource.name = bdata.name.split('/')[-1]
        resource.read(bdata, os.path.getsize(args.file), path=str(args.file))
        resource.save_converted(os.path.join('out', bdata.name).replace('\\', '/'))

print(f'Finished. Execution time: {time.time() - start_time} seconds')
