import argparse
import os
import pathlib
import time
from collections import defaultdict
from multiprocessing import Pool, cpu_count

import settings
from guess_parser import get_resource_class
from parsers.resources.collections import ResourceDirectory, MultiprocessResourceDirectory
from src.require_resource import require_file
from utils import my_import
from tqdm import tqdm

start_time = time.time()

resource = argparse.ArgumentParser()
resource.add_argument('file', type=pathlib.Path)
args = resource.parse_args()

files_to_open = []
if os.path.isdir(args.file):
    for subdir, dirs, files in os.walk(args.file):
        files_to_open += [subdir + '/' + f for f in files]
else:
    files_to_open = [str(args.file)]


def process_file(path):
    try:
        block = require_file(path)
        serializer_class_name = settings.SERIALIZER_CLASSES.get(block.__class__.__name__)
        serializer_class = None
        if serializer_class_name:
            try:
                serializer_class = my_import(f'serializers.{serializer_class_name}')
            except ImportError:
                pass
        if not serializer_class_name or not serializer_class:
            raise NotImplementedError(f'Serializer for resource {block.__class__.__name__} not implemented!')
        serializer = serializer_class()
        serializer.serialize(block, path, None)
        print('Serialized ' + path)
    except Exception as ex:
        return ex


with Pool(processes=cpu_count()
          if settings.multiprocess_processes_count == 0
          else settings.multiprocess_processes_count) as pool:
    results = list(tqdm((pool.apply(process_file, (f,)) for f in files_to_open), total=len(files_to_open)))
skipped_resources = [(files_to_open[i], exc) for i, exc in enumerate(results) if isinstance(exc, Exception)]
if skipped_resources:
    skipped_map = defaultdict(lambda: list())
    for name, ex in skipped_resources:
        path, name = '/'.join(name.split('/')[:-1]), name.split('/')[-1]
        skipped_map[path].append((name, f'{ex.__class__.__name__}: {str(ex)}'))
    for path, skipped in skipped_map.items():
        os.makedirs(f'out/{path}', exist_ok=True)
        skipped.sort(key=lambda x: x[0])
        with open(f'out/{path}/skipped.txt', 'w') as f:
            for item in skipped:
                f.write("%s\t\t%s\n" % item)

print(f'Finished. Execution time: {time.time() - start_time} seconds')
