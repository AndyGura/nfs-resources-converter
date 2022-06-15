import os
import tempfile

import settings


def get_blender_save_script(out_blend_name=None):
    script = '\n\n\n'
    if out_blend_name:
        script += f'\n\nbpy.ops.wm.save_as_mainfile(filepath="{out_blend_name}.blend")'
    return script


def run_blender(path, script, out_blend_name=None):
    if out_blend_name:
        script += '\n\n' + get_blender_save_script(out_blend_name=out_blend_name)
    script += '\nquit()'
    script_file = tempfile.NamedTemporaryFile(delete=False, mode='w')
    script_file.write(script)
    script_file.flush()
    os.system(f"cd {path} && {settings.blender_executable} --python {script_file.name} --background")
    os.unlink(script_file.name)
