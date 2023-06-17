import os
import tempfile
from copy import deepcopy
from distutils.dir_util import copy_tree
from itertools import chain
from logging import warning
from pathlib import Path
from typing import Dict

import eel

from library import require_file, require_resource
from library.loader import clear_file_cache
from library.utils.file_utils import remove_file_or_directory
from library.utils.file_utils import start_file
from serializers import get_serializer, DataTransferSerializer


def __apply_delta_to_resource(resource_id, resource, changes: Dict):
    suffix = '/' if '__' in resource_id else '__'
    for delta in changes:
        if not delta['id'].startswith(resource_id + suffix):
            warning('Skipped change ' + delta['id'] + '. Wrong ID')
        sub_id = delta['id'][len(resource_id) + len(suffix):]
        field = resource
        for subkey in sub_id.split('/'):
            try:
                field = getattr(field, subkey)
            except AttributeError:
                if isinstance(field.value, list):
                    field = field[int(subkey)]
                else:
                    field = field[subkey]
        field.value = delta['value']


def run_gui_editor(file_path):
    # create directory for all files, needed by GUI
    static_dir = tempfile.TemporaryDirectory()
    static_path = static_dir.name
    copy_tree('frontend/dist/gui', static_path)

    # app state
    current_file_id = None
    current_file = None

    def init_eel_state():

        @eel.expose
        def on_angular_ready():
            eel.open_file(file_path)

        @eel.expose
        def open_file(path: str, force_reload: bool = False):
            nonlocal current_file
            nonlocal current_file_id
            try:
                if (force_reload):
                    clear_file_cache(path)
                current_file = require_file(path)
                current_file_id = current_file.block_state['id']
            except Exception as ex:
                current_file = ex
                current_file_id = path
            return DataTransferSerializer().serialize(current_file)

        @eel.expose
        def open_file_with_system_app(path: str):
            if path.startswith('/') or path.startswith('\\'):
                path = path[1:]
            start_file(os.path.join(static_path, path))

        @eel.expose
        def save_file(path: str, changes: Dict):
            __apply_delta_to_resource(current_file_id, current_file, changes)
            bts = current_file.to_bytes()
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
        def serialize_resource(id: str, settings_patch={}):
            resource, top_level_resource = require_resource(id)
            serializer = get_serializer(resource.block)
            path = os.path.join(static_path, 'resources', *id.split('/'))
            if settings_patch:
                serializer.patch_settings(settings_patch)
            serializer.serialize(resource, path)
            normal_slashes_path = path.replace('\\', '/')
            exported_file_paths = [str(x)[len(static_path):]
                                   for x in chain(Path(normal_slashes_path).glob("**/*"),
                                                  Path(normal_slashes_path[:normal_slashes_path.rindex('/')]).glob(
                                                      normal_slashes_path[
                                                      (normal_slashes_path.rindex('/') + 1):] + '.*'))
                                   if not x.is_dir()]
            return [x.replace('\\', '/') for x in exported_file_paths]

        @eel.expose
        def serialize_resource_tmp(id: str, changes: Dict, settings_patch={}):
            resource, _ = require_resource(id)
            resource = deepcopy(resource)
            __apply_delta_to_resource(id, resource, changes)
            serializer = get_serializer(resource.block)
            path = os.path.join(static_path, 'resources_tmp', *id.split('/'))
            if settings_patch:
                serializer.patch_settings(settings_patch)
            serializer.serialize(resource, path)
            normal_slashes_path = path.replace('\\', '/')
            return [str(x)[len(static_path):]
                    for x in chain(Path(normal_slashes_path).glob("**/*"),
                                   Path(normal_slashes_path[:normal_slashes_path.rindex('/')]).glob(
                                       normal_slashes_path[(normal_slashes_path.rindex('/') + 1):] + '.*'))
                    if not x.is_dir()]

        @eel.expose
        def deserialize_resource(id: str):
            resource, _ = require_resource(id)
            serializer = get_serializer(resource.block)
            path = os.path.join(static_path, 'resources_tmp', *id.split('/'))
            serializer.deserialize(path, resource)
            remove_file_or_directory(os.path.join(static_path, 'resources', *id.split('/')))
            remove_file_or_directory(os.path.join(static_path, 'resources_tmp', *id.split('/')))
            return DataTransferSerializer().serialize(current_file)

    eel.init(static_path)
    init_eel_state()
    eel.start('index.html', port=0)
    static_dir.cleanup()
