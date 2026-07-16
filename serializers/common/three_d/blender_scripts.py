import os
import tempfile

import config
from library.utils.logging_setup import run_command_and_log

general_config = config.general_config()


def get_blender_save_script(out_blend_name=None):
    temp_blend_name = out_blend_name.replace("\\", "/")
    script = '\n\n\n'
    if out_blend_name:
        script += f'\n\nbpy.ops.wm.save_as_mainfile(filepath="{temp_blend_name}.blend")'
    return script


def run_blender(path, script, out_blend_name=None):
    working_dir = path.replace("\\", "/")
    script = f"""import bpy
import os
os.chdir("{working_dir}")
""" + script
    if out_blend_name:
        script += '\n\n' + get_blender_save_script(out_blend_name=out_blend_name)
    script += '\nquit()'
    script_file = tempfile.NamedTemporaryFile(delete=False, mode='w')
    script_file.write(script)
    script_file.flush()
    script_file.close()
    command = f'"{general_config.blender_executable}" --python {script_file.name} --background'
    run_command_and_log(command, capture_output=general_config.print_blender_log)
    os.unlink(script_file.name)
