import os
import tempfile

import config

general_config = config.general_config()


def get_log_throwaway_suffix():
    if os.name == 'nt':
        return " >NUL 2>&1"
    else:
        return " >/dev/null 2>&1"


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
    if not general_config.print_blender_log:
        command += get_log_throwaway_suffix()
    os.system(command)
    os.unlink(script_file.name)
