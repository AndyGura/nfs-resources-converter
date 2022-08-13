import inspect
import os
import sys
import traceback

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

import argparse
import pathlib
import time
from collections import defaultdict
from multiprocessing import Pool, cpu_count

from tqdm import tqdm

import settings
from library import require_file
from library.utils import format_exception
from serializers import get_serializer

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


def export_file(path):
    try:
        data = require_file(path)
        serializer = get_serializer(data.block)
        serializer.serialize(data, f'out/{path}')
    except Exception as ex:
        if settings.print_errors:
            traceback.print_exc()
        return ex


processes = cpu_count() if settings.multiprocess_processes_count == 0 else settings.multiprocess_processes_count
with Pool(processes=processes) as pool:
    pbar = tqdm(total=len(files_to_open))
    results = [pool.apply_async(export_file, (f,), callback=lambda *a: pbar.update()) for f in files_to_open]
    results = list(result.get() for result in results)
pbar.close()

skipped_resources = [(files_to_open[i], exc) for i, exc in enumerate(results) if isinstance(exc, Exception)]
if skipped_resources:
    skipped_map = defaultdict(lambda: list())
    for name, ex in skipped_resources:
        path, name = '/'.join(name.split('/')[:-1]), name.split('/')[-1]
        skipped_map[path].append((name, format_exception(ex)))
    for path, skipped in skipped_map.items():
        os.makedirs(f'out/{path}', exist_ok=True)
        skipped.sort(key=lambda x: x[0])
        with open(f'out/{path}/skipped.txt', 'w') as f:
            for item in skipped:
                f.write("%s\t\t%s\n" % item)

print(f'Finished. Execution time: {time.time() - start_time} seconds')
