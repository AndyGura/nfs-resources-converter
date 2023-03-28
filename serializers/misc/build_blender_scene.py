import os
import sys
import tempfile

from string import Template

__blender_script_template = Template("""
import bpy
import json
import os
from rna_prop_ui import rna_idprop_value_to_python


def parse_curve_obj(object):
    curve = bpy.data.curves[object.data.name]
    spline = curve.splines[0]
    is_cyclic = spline.use_cyclic_u
    points = list(map(lambda p: {
        "x": p.co.x + object.location.x,
        "y": p.co.y + object.location.y,
        "z": p.co.z + object.location.z
    }, spline.points))
    return {
        "name": object.name,
        "cyclic": is_cyclic,
        "points": points,
        **{x: rna_idprop_value_to_python(object[x]) for x in object.keys() if x != '_RNA_UI'}
    }

def parse_dummy_obj(object):
    object.rotation_mode = 'QUATERNION'
    return {
        "name": object.name,
        "position": {
            "x": object.location.x,
            "y": object.location.y,
            "z": object.location.z,
        },
        "rotation": {
            "x": object.rotation_quaternion.x,
            "y": object.rotation_quaternion.y,
            "z": object.rotation_quaternion.z,
            "w": object.rotation_quaternion.w,
        },
        **{x: object[x] for x in object.keys() if x != '_RNA_UI'}
    }
    
def get_rigid_body_description(obj, export_body_parameters=True):
    body = obj.rigid_body
    obj.rotation_mode = 'QUATERNION'
    meta = {
        "name": obj.name,
        "position": { 
            'x': obj.location.x, 
            'y': obj.location.y, 
            'z': obj.location.z,
        },
        # FIXME relative rotation
        "rotation": { 'x': obj.rotation_quaternion.x, 'y': obj.rotation_quaternion.y, 'z': obj.rotation_quaternion.z, 'w': obj.rotation_quaternion.w },
        "shape": {
            "shape": body.collision_shape,
        },
    }
    if (export_body_parameters):
        meta['body'] = {
            "dynamic": body.type == "ACTIVE",
            "mass": body.mass,
            "restitution": body.restitution,
            "friction": body.friction,
        }
    parent = obj.parent
    while parent:
        meta['position']['x'] -= parent.location.x
        meta['position']['y'] -= parent.location.y
        meta['position']['z'] -= parent.location.z
        parent = parent.parent
    meta['position']['x'] = round(meta['position']['x'], 6)
    meta['position']['y'] = round(meta['position']['y'], 6)
    meta['position']['z'] = round(meta['position']['z'], 6)
    if meta['shape']['shape'] == 'SPHERE':
        meta['shape']['radius'] = max(obj.dimensions.x, obj.dimensions.y, obj.dimensions.z) / 2
    elif meta['shape']['shape'] == 'BOX':
        meta['shape']['dimensions'] = { 'x': obj.dimensions.x, 'y': obj.dimensions.y, 'z': obj.dimensions.z }
    elif meta['shape']['shape'] in ['CONE', 'CYLINDER']:
        meta['shape']['radius'] = max(obj.dimensions.x, obj.dimensions.y) / 2
        meta['shape']['height'] = obj.dimensions.z
    elif meta['shape']['shape'] == 'CAPSULE':
        meta['shape']['radius'] = max(obj.dimensions.x, obj.dimensions.y) / 2
        meta['shape']['centersDistance'] = obj.dimensions.z - max(obj.dimensions.x, obj.dimensions.y)
    elif meta['shape']['shape'] == 'CONVEX_HULL':
        meta['shape']['vertices'] = [{ 'x': v.co.x, 'y': v.co.y, 'z': v.co.z } for v in obj.data.vertices]
    elif meta['shape']['shape'] == 'MESH':
        meta['shape']['vertices'] = [{ 'x': v.co.x, 'y': v.co.y, 'z': v.co.z } for v in obj.data.vertices]
        import bmesh
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        meta['shape']['faces'] = [[v.index for v in f.verts] for f in bm.faces]
        bm.free()
    elif meta['shape']['shape'] == 'COMPOUND':
        meta['shape']['children'] = [get_rigid_body_description(sub_obj, export_body_parameters=False)
                                    for sub_obj in bpy.context.scene.objects
                                    if sub_obj.rigid_body is not None and sub_obj.parent == obj]
    else:
        raise NotImplementedError(f'GG does not support exporting rigid body {meta["shape"]["shape"]} shape')
    return meta

if "$src_file":
    bpy.ops.wm.open_mainfile(filepath="$src_file")

# compound metadata
metadata = {"curves": [], "dummies": [], "rigidBodies": []}
for obj in filter(lambda x: x.type == "CURVE", bpy.data.objects):
    metadata["curves"].append(parse_curve_obj(obj))
for obj in filter(lambda x: x.type == "EMPTY", bpy.data.objects):
    metadata["dummies"].append(parse_dummy_obj(obj))

# saving scene
for obj in bpy.context.scene.objects:
    include_in_export = obj.type in ["MESH", "LIGHT", "CURVE"]
    include_in_glb = not obj.hide_render
    obj.select_set(state=include_in_export and include_in_glb)
    if not include_in_export:
        continue
    for modifier in obj.modifiers:
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    if obj.rigid_body is not None and (obj.parent is None or obj.parent.rigid_body is None or obj.parent.rigid_body.collision_shape != 'COMPOUND'):
        metadata["rigidBodies"].append(get_rigid_body_description(obj))
    
bpy.ops.export_scene.gltf(export_format="GLB",
                          export_copyright="Gurakl Games",
                          export_texcoords=True,
                          export_normals=True,
                          export_tangents=True,
                          export_materials='$export_materials',
                          export_colors=True,
                          export_cameras=False,
                          export_lights=True,
                          export_extras=True,
                          export_yup=False,
                          export_apply=False,
                          export_animations=False,
                          use_selection=True,
                          export_skins=False,
                          export_morph=False,
                          filepath="$file_name.glb")
# saving metadata
with open("$file_name.meta", 'w') as outfile:
    json.dump(metadata, outfile)""")


def construct_blender_export_script(file_name, src_file="", export_materials="EXPORT") -> str:
    return __blender_script_template.substitute({
        'src_file': src_file,
        'file_name': file_name,
        'export_materials': export_materials
    })

if __name__ == "__main__":
    # will be invoked if this module is being run directly, but not via import
    skip_textures = sys.argv[1] == '--skip-textures'
    if skip_textures:
        files = sys.argv[2:]
    else:
        files = sys.argv[1:]

    script = ""
    for file in files:
        if file.startswith('./'):
            file = file[2:]
        full_path = os.path.join(os.getcwd(), file)
        script += '\n\n\n' + construct_blender_export_script(src_file=full_path,
                                                             file_name=full_path[:full_path.rindex('.')],
                                                             export_materials="NONE" if skip_textures else "EXPORT")

    script_file = tempfile.NamedTemporaryFile(delete=False, mode='w')
    script_file.write(script)
    script_file.flush()
    os.system(f"blender --python {script_file.name} --background")
    os.unlink(script_file.name)
