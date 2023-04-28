import os
from distutils.dir_util import copy_tree
import tempfile
from logging import warn
from pathlib import Path
from typing import Dict

import eel

from library import require_file, require_resource
from library.loader import clear_file_cache
from resources.utils import determine_palette_for_8_bit_bitmap
from serializers import get_serializer, DataTransferSerializer


def run_gui_editor(file_path):
    # create directory for all files, needed by GUI
    service_dir = tempfile.TemporaryDirectory()
    static_dir = service_dir.name
    copy_tree('frontend/dist/gui', static_dir)

    def init_eel_state():
        from library.helpers.data_wrapper import DataWrapper
        state = DataWrapper({
            'current_file_id': None,
            'current_file': None,
            'serialized_temporary_files': {},
        })

        @eel.expose
        def on_angular_ready():
            eel.open_file(file_path)

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
        def run_custom_action(resource_id: str, action: Dict, args: Dict):
            _, resource = require_resource(resource_id)
            action_func = getattr(resource.block, f'action_{action["method"]}')
            action_func(resource, **args)
            return DataTransferSerializer().serialize(resource)

        @eel.expose
        def serialize_resource(id: str, settings_patch = {}):
            if state.serialized_temporary_files.get(id):
                path, exported_file_paths, resource, top_level_resource, serializer = \
                state.serialized_temporary_files[id]
                for path in exported_file_paths:
                    if not os.path.exists(path):
                        del state.serialized_temporary_files[id]
                        return serialize_resource(id)
            else:
                resource, top_level_resource = require_resource(id)
                serializer = get_serializer(resource.block)
                path = static_dir + '/resources/' + id
                if settings_patch:
                    serializer.patch_settings(settings_patch)
                serializer.serialize(resource, path)
                exported_file_paths = [str(x)[len(static_dir):] for x in Path(path).glob("**/*") if not x.is_dir()]
                state.serialized_temporary_files[id] = path, exported_file_paths, resource, top_level_resource, serializer
            return exported_file_paths

        @eel.expose
        def deserialize_resource(id: str):
            if not state.serialized_temporary_files.get(id):
                return
            path, exported_file_paths, resource, top_level_resource, serializer = \
            state.serialized_temporary_files[id]
            serializer.deserialize(path, resource)
            del state.serialized_temporary_files[id]
            return DataTransferSerializer().serialize(top_level_resource)

        @eel.expose
        def determine_8_bit_bitmap_palette(bitmap_id: str):
            bitmap, _ = require_resource(bitmap_id)
            palette = determine_palette_for_8_bit_bitmap(bitmap)
            if palette:
                return DataTransferSerializer().serialize(palette)
            return None

    eel.init(static_dir)
    init_eel_state()
    eel.start('index.html')
    service_dir.cleanup()
