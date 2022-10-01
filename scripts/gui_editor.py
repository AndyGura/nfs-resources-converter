import argparse
import inspect
import os
import pathlib
import sys
import tempfile
from logging import warn
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


def init_eel_state():
    from library.helpers.data_wrapper import DataWrapper
    state = DataWrapper({
        'current_file_id': None,
        'current_file': None,
        'serialized_temporary_files': {},
    })

    @eel.expose
    def on_angular_ready():
        eel.open_file(str(args.file))

    @eel.expose
    def open_file(path: str, force_reload: bool = False):
        try:
            if (force_reload):
                clear_file_cache(path)
            state.current_file = require_file(path)
            state.current_file_id = state.current_file.block_state['id']
        except Exception as ex:
            state.current_file = ex
            state.current_file_id = path
        return DataTransferSerializer().serialize(state.current_file)

    @eel.expose
    def save_file(path: str, changes: Dict):
        for delta in changes:
            if not delta['id'].startswith(state.current_file_id + '__'):
                warn('Skipped change ' + delta['id'] + '. Wrong ID')
            sub_id = delta['id'][len(state.current_file_id) + 2:]
            field = state.current_file
            for subkey in sub_id.split('/'):
                try:
                    field = getattr(field, subkey)
                except AttributeError:
                    if isinstance(field.value, list):
                        field = field[int(subkey)]
                    else:
                        field = field[subkey]
            field.value = delta['value']
        bts = state.current_file.to_bytes()
        f = open(path, 'wb')
        f.write(bts)
        f.close()
        clear_file_cache(path)

    @eel.expose
    def serialize_resource(id: str):
        if state.serialized_temporary_files.get(id):
            path, exported_file_paths, tmpdir, resource, top_level_resource, serializer = state.serialized_temporary_files[id]
            for path in exported_file_paths:
                if not os.path.exists(path):
                    del state.serialized_temporary_files[id]
                    return serialize_resource(id)
        else:
            tmpdir = tempfile.TemporaryDirectory()
            resource, top_level_resource = require_resource(id)
            serializer = get_serializer(resource.block)
            path = tmpdir.name + '/' + id.split('/')[-1]
            serializer.serialize(resource, path)
            exported_file_paths = [path + '.png']  # TODO make serializer return list of files
            state.serialized_temporary_files[id] = path, exported_file_paths, tmpdir, resource, top_level_resource, serializer
        [start_file(x) for x in exported_file_paths]
        return exported_file_paths

    @eel.expose
    def deserialize_resource(id: str):
        if not state.serialized_temporary_files.get(id):
            return
        path, exported_file_paths, tmpdir, resource, top_level_resource, serializer = state.serialized_temporary_files[id]
        serializer.deserialize(path, resource)
        tmpdir.cleanup()
        del state.serialized_temporary_files[id]
        return DataTransferSerializer().serialize(top_level_resource)

    @eel.expose
    def determine_8_bit_bitmap_palette(bitmap_id: str):
        bitmap, _ = require_resource(bitmap_id)
        palette = determine_palette_for_8_bit_bitmap(bitmap)
        if palette:
            return DataTransferSerializer().serialize(palette)
        return None

eel.init('frontend/dist/gui')
init_eel_state()
eel.start('index.html')
