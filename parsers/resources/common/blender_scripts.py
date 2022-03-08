import os
import tempfile

from sys import path

path.append(os.path.realpath(os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                          '../../../../engine/build_tools')))
from build_blender_scene import construct_blender_export_script


def get_blender_save_script(out_glb_name=None, export_materials='EXPORT', out_blend_name=None):
    script = '\n\n\n'
    if out_glb_name:
        script += '\n\n' + construct_blender_export_script(file_name=out_glb_name, export_materials=export_materials)
    if out_blend_name:
        script += f'\n\nbpy.ops.wm.save_as_mainfile(filepath="{out_blend_name}.blend")'
    return script


def run_blender(path, script, out_glb_name=None, export_materials='EXPORT', out_blend_name=None):
    if out_glb_name or out_blend_name:
        script += '\n\n' + get_blender_save_script(out_glb_name=out_glb_name,
                                                   export_materials=export_materials,
                                                   out_blend_name=out_blend_name)
    script += '\nquit()'
    script_file = tempfile.NamedTemporaryFile(delete=False, mode='w')
    script_file.write(script)
    script_file.flush()
    os.system(f"cd {path} && blender --python {script_file.name} --background")
    os.unlink(script_file.name)
