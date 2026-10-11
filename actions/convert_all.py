import os
import time
import traceback
from collections import defaultdict
from multiprocessing import Pool, cpu_count

from tqdm import tqdm

import config
from library import require_file
from library.utils import format_exception, path_join
from library.utils.logging_setup import setup_logging, is_stdout_redirected
from serializers import get_serializer


def export_file(base_input_path, path, out_path, settings):
    try:
        (name, block, data) = require_file(path)
        serializer = get_serializer(block, data)
        serializer.patch_settings(settings)
        rel_path = path[len(base_input_path) :]
        if not rel_path:
            is_dir = serializer.is_dir
            # DelegateBlock
            if callable(is_dir):
                is_dir = is_dir(block, data)
            if is_dir:
                rel_path = path.split('/')[-1]
        serializer.serialize(data, f'{out_path}/{rel_path}', id=name, block=block)
    except Exception as ex:
        traceback.print_exc()
        return ex


def convert_all(path, out_path, preset=None):
    """
    Convert a file, or every file in a directory tree, to common formats.

    Args:
        path: Input file or directory
        out_path: Output directory
        preset: Conversion preset name, None for the default conversion settings
    """
    start_time = time.time()
    # resolved here, so a missing preset fails before any work, and passed to the workers explicitly
    settings = config.conversion_preset_settings(preset)
    base_input_path = str(path)
    files_to_open = []
    if os.path.isdir(path):
        for subdir, dirs, files in os.walk(path):
            files_to_open += [path_join(subdir, f) for f in files]
    else:
        files_to_open = [str(path).replace('\\', '/')]

    processes = settings['multiprocess_processes_count'] or cpu_count()
    import logging

    logging.info(
        f'Starting conversion of {len(files_to_open)} files from {path} to {out_path} using {processes} processes, '
        + (f'preset "{preset}"' if preset else 'no preset')
    )
    with Pool(processes=processes, initializer=setup_logging, initargs=(is_stdout_redirected(),)) as pool:
        pbar = tqdm(total=len(files_to_open))
        results = [
            pool.apply_async(export_file, (base_input_path, f, out_path, settings), callback=lambda *a: pbar.update())
            for f in files_to_open
        ]
        results = list(result.get() for result in results)
    pbar.close()

    skipped_resources = [(files_to_open[i], exc) for i, exc in enumerate(results) if isinstance(exc, Exception)]
    if skipped_resources:
        skipped_map = defaultdict(lambda: list())
        for name, ex in skipped_resources:
            name = name.replace('\\', '/')
            path, name = '/'.join(name.split('/')[:-1]), name.split('/')[-1]
            skipped_map[path].append((name, format_exception(ex)))
        for path, skipped in skipped_map.items():
            path_suffix = path[len(base_input_path) :]
            if path_suffix.startswith('/'):
                path_suffix = path_suffix[1:]
            skipped_txt_output_path = path_join(out_path, path_suffix, 'skipped.txt')
            os.makedirs(os.path.dirname(skipped_txt_output_path), exist_ok=True)
            skipped.sort(key=lambda x: x[0])
            with open(skipped_txt_output_path, 'w') as f:
                for item in skipped:
                    f.write('%s\t\t%s\n' % item)

    print(f'Finished. Execution time: {time.time() - start_time} seconds')
    print(f'Support me :) >>>  https://www.buymeacoffee.com/andygura <<<')
