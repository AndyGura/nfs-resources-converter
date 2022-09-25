import argparse
import inspect
import os
import pathlib
import sys
import tempfile
from typing import Dict

import eel

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

from resources.utils import determine_palette_for_8_bit_bitmap
from library import require_file, require_resource

from library.loader import clear_file_cache
from library.utils.start_file import start_file
from serializers import get_serializer, DataTransferSerializer

resource = argparse.ArgumentParser()
resource.add_argument('file', type=pathlib.Path)
args = resource.parse_args()

eel.init('frontend/dist/gui')

current_file = None

serialized_temporary_files = {}


@eel.expose
def on_angular_ready():
    eel.open_file(str(args.file))


@eel.expose
def open_file(path: str):
    try:
        current_file = require_file(path)
    except Exception as ex:
        current_file = ex
    return DataTransferSerializer().serialize(current_file)


@eel.expose
def save_file(path: str, file_data: Dict):
    current_file = DataTransferSerializer().deserialize(file_data)
    bts = current_file.to_bytes()
    f = open(path, 'wb')
    f.write(bts)
    f.close()
    clear_file_cache(path)


@eel.expose
def serialize_resource(id: str):
    if serialized_temporary_files.get(id):
        path, exported_file_paths, tmpdir, resource, top_level_resource, serializer = serialized_temporary_files[id]
        for path in exported_file_paths:
            if not os.path.exists(path):
                del serialized_temporary_files[id]
                return serialize_resource(id)
    else:
        tmpdir = tempfile.TemporaryDirectory()
        resource, top_level_resource = require_resource(id)
        serializer = get_serializer(resource.block)
        path = tmpdir.name + '/' + id.split('/')[-1]
        serializer.serialize(resource, path)
        exported_file_paths = [path + '.png']  # TODO make serializer return list of files
        serialized_temporary_files[id] = path, exported_file_paths, tmpdir, resource, top_level_resource, serializer
    [start_file(x) for x in exported_file_paths]
    return exported_file_paths


@eel.expose
def deserialize_resource(id: str):
    if not serialized_temporary_files.get(id):
        return
    path, exported_file_paths, tmpdir, resource, top_level_resource, serializer = serialized_temporary_files[id]
    serializer.deserialize(path, resource)
    tmpdir.cleanup()
    del serialized_temporary_files[id]
    return DataTransferSerializer().serialize(top_level_resource)


@eel.expose
def determine_8_bit_bitmap_palette(bitmap_id: str):
    bitmap, _ = require_resource(bitmap_id)
    palette = determine_palette_for_8_bit_bitmap(bitmap)
    if palette:
        return DataTransferSerializer().serialize(palette)
    return None


eel.start('index.html')
