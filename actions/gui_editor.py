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
from serializers import get_serializer
from serializers.misc.json_utils import convert_bytes


def __apply_delta_to_resource(resource_id, resource, changes: Dict):
    suffix = '/' if '__' in resource_id else '__'
    for delta in changes:
        if not delta['id'].startswith(resource_id + suffix):
            warning('Skipped change ' + delta['id'] + '. Wrong ID')
        sub_id = delta['id'][len(resource_id) + len(suffix):]
        field = resource
        for subkey in sub_id.split('/')[:-1]:
            if isinstance(field, list):
                field = field[int(subkey)]
            else:
                field = field.get(subkey)
        if isinstance(field, list):
            field[int(sub_id.split('/')[-1])] = delta['value']
        else:
            field[sub_id.split('/')[-1]] = delta['value']


def run_gui_editor(file_path):
    # create directory for all files, needed by GUI
    static_dir = tempfile.TemporaryDirectory()
    static_path = static_dir.name
    copy_tree('frontend/dist/gui', static_path)

    # app state
    current_file_name = None
    current_file_data = None
    current_file_block = None

    def init_eel_state():

        @eel.expose
        def on_angular_ready():
            eel.open_file(file_path)

        @eel.expose
        def open_file(path: str, force_reload: bool = False):
            nonlocal current_file_name
            nonlocal current_file_data
            nonlocal current_file_block
            try:
                if (force_reload):
                    clear_file_cache(path)
                (name, block, data) = require_file(path)
                current_file_name = name
                current_file_data = data
                current_file_block = block
            except Exception as ex:
                current_file_data = {
                    'error_class': ex.__class__.__name__,
                    'error_text': str(ex),
                }
                current_file_name = path
                current_file_block = None
            return {
                'name': current_file_name,
                'schema': current_file_block.schema if current_file_block else None,
                'data': convert_bytes(current_file_data)
            }

        @eel.expose
        def open_file_with_system_app(path: str):
            if path.startswith('/') or path.startswith('\\'):
                path = path[1:]
            start_file(os.path.join(static_path, path))

        @eel.expose
        def save_file(path: str, changes: Dict):
            __apply_delta_to_resource(current_file_name, current_file_data, changes)
            bts = current_file_block.pack(current_file_data)
            f = open(path, 'wb')
            f.write(bts)
            f.close()
            clear_file_cache(path)

        @eel.expose
        def run_custom_action(resource_id: str, action: Dict, args: Dict):
            (name, res_block, resource), _ = require_resource(resource_id)
            action_func = getattr(res_block, f'action_{action["method"]}')
            action_func(resource, **args)
            return {
                'name': name,
                'schema': res_block.schema,
                'data': convert_bytes(resource)
            }

        @eel.expose
        def serialize_resource(id: str, settings_patch={}):
            (_, res_block, res), (_, top_level_block, top_level_res) = require_resource(id)
            serializer = get_serializer(res_block, res)
            path = os.path.join(static_path, 'resources', *id.split('/'))
            if settings_patch:
                serializer.patch_settings(settings_patch)
            serializer.serialize(res, path, id, res_block)
            normal_slashes_path = path.replace('\\', '/')
            exported_file_paths = [str(x)[len(static_path):]
                                   for x in chain(Path(normal_slashes_path).glob("**/*"),
                                                  Path(normal_slashes_path[:normal_slashes_path.rindex('/')]).glob(
                                                      normal_slashes_path[
                                                      (normal_slashes_path.rindex('/') + 1):] + '.*'))
                                   if not x.is_dir()]
            return [x.replace('\\', '/') for x in exported_file_paths]

        @eel.expose
        # serialize resource with ability to serialize it back.
        # serializes data in any case
        # returns file list and flag is it possible to deserialize files back
        def serialize_reversible(id: str, changes: Dict):
            (id, res_block, resource), _ = require_resource(id)
            resource = deepcopy(resource)
            __apply_delta_to_resource(id, resource, changes)
            serializer = get_serializer(res_block, resource)
            path = os.path.join(static_path, 'resources_edit', *id.split('/'))
            reverse_flag = serializer.setup_for_reversible_serialization()
            serializer.serialize(resource, path, id, res_block)
            normal_slashes_path = path.replace('\\', '/')
            return [str(x)[len(static_path):]
                    for x in chain(Path(normal_slashes_path).glob("**/*"),
                                   Path(normal_slashes_path[:normal_slashes_path.rindex('/')]).glob(
                                       normal_slashes_path[(normal_slashes_path.rindex('/') + 1):] + '.*'))
                    if not x.is_dir()], reverse_flag

        @eel.expose
        def serialize_resource_tmp(id: str, changes: Dict, settings_patch={}):
            (_, res_block, resource), _ = require_resource(id)
            resource = deepcopy(resource)
            __apply_delta_to_resource(id, resource, changes)
            serializer = get_serializer(res_block, resource)
            path = os.path.join(static_path, 'resources_tmp', *id.split('/'))
            if settings_patch:
                serializer.patch_settings(settings_patch)
            serializer.serialize(resource, path, id, res_block)
            normal_slashes_path = path.replace('\\', '/')
            return [str(x)[len(static_path):]
                    for x in chain(Path(normal_slashes_path).glob("**/*"),
                                   Path(normal_slashes_path[:normal_slashes_path.rindex('/')]).glob(
                                       normal_slashes_path[(normal_slashes_path.rindex('/') + 1):] + '.*'))
                    if not x.is_dir()]

        @eel.expose
        def deserialize_resource(id: str):
            (id, res_block, resource), _ = require_resource(id)
            serializer = get_serializer(res_block, resource)
            path = os.path.join(static_path, 'resources_edit', *id.split('/'))
            updated_data = serializer.deserialize(path, id, res_block)
            current_file_data.clear()
            current_file_data.update(updated_data)
            remove_file_or_directory(os.path.join(static_path, 'resources', *id.split('/')))
            remove_file_or_directory(os.path.join(static_path, 'resources_tmp', *id.split('/')))
            remove_file_or_directory(os.path.join(static_path, 'resources_edit', *id.split('/')))
            return convert_bytes(current_file_data)

    eel.init(static_path)
    init_eel_state()
    eel.start('index.html', port=0)
    static_dir.cleanup()
