import os
import tempfile

from sys import path


def get_blender_save_script(export_materials='EXPORT', out_blend_name=None):
    script = '\n\n\n'
    if out_blend_name:
        script += f'\n\nbpy.ops.wm.save_as_mainfile(filepath="{out_blend_name}.blend")'
    return script


def run_blender(path, script, export_materials='EXPORT', out_blend_name=None):
    if out_blend_name:
        script += '\n\n' + get_blender_save_script(export_materials=export_materials,
                                                   out_blend_name=out_blend_name)
    script += '\nquit()'
    script_file = tempfile.NamedTemporaryFile(delete=False, mode='w')
    script_file.write(script)
    script_file.flush()
    os.system(f"cd {path} && blender --python {script_file.name} --background")
    os.unlink(script_file.name)
