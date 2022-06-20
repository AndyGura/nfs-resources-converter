# generic
blender_executable = 'blender'
ffmpeg_executable = 'ffmpeg'
# example of absolute path for windows '"C:/Program Files/Blender Foundation/Blender 3.2/blender.exe"'

multiprocess_directory_blacklist = [
    'FRONTEND/ART/CONTROL',  # here we have SHPI archives, which use palette from neighbour file
    'FRONTEND/GART/CONTROL',  # the same here
]

save_unknown_values = False

# images
images__save_inline_palettes = False

# media
save_media_files = True
audio__save_car_sfx_loops = False

# 3D
geometry__save_obj = False
geometry__save_blend = True
geometry__skip_car_wheel_polygons = False

# maps export settings
maps__save_as_chunked = False
maps__save_collisions = False    # this one will consume time...


# returned script will be executed in blender for every exported scene
# geometry kind: 'car', 'map', 'terrain_chunk', 'prop'
def geometry__additional_exporter(dest_file_name, geometry_kind):
    return ""
#     from string import Template
#     __blender_script_template = Template("""
# import bpy
# import json
# import os
# from rna_prop_ui import rna_idprop_value_to_python
#
# def parse_curve_obj(object):
#     curve = bpy.data.curves[object.data.name]
#     spline = curve.splines[0]
#     is_cyclic = spline.use_cyclic_u
#     points = list(map(lambda p: {
#         "x": p.co.x + object.location.x,
#         "y": p.co.y + object.location.y,
#         "z": p.co.z + object.location.z
#     }, spline.points))
#     return {
#         "name": object.name,
#         "cyclic": is_cyclic,
#         "points": points,
#         **{x: rna_idprop_value_to_python(object[x]) for x in object.keys() if x != '_RNA_UI'}
#     }
#
# def parse_dummy_obj(object):
#     return {
#         "name": object.name,
#         "position": {
#             "x": object.location.x,
#             "y": object.location.y,
#             "z": object.location.z,
#         },
#         "rotation": {
#             "x": object.rotation_quaternion.x,
#             "y": object.rotation_quaternion.y,
#             "z": object.rotation_quaternion.z,
#             "w": object.rotation_quaternion.w,
#         },
#         **{x: object[x] for x in object.keys() if x != '_RNA_UI'}
#     }
# # compound metadata
# metadata = {"curves": [], "dummies": [], "rigidBodies": []}
# for obj in filter(lambda x: x.type == "CURVE", bpy.data.objects):
#     metadata["curves"].append(parse_curve_obj(obj))
# for obj in filter(lambda x: x.type == "EMPTY", bpy.data.objects):
#     metadata["dummies"].append(parse_dummy_obj(obj))
#
# # saving scene
# for obj in bpy.data.objects:
#     include_in_export = obj.type in ["MESH", "LIGHT"]
#     obj.select_set(state=include_in_export)
#     if not include_in_export:
#         continue
#     if obj.rigid_body is not None:
#         body = obj.rigid_body
#         metadata["rigidBodies"].append({
#             "name": obj.name,
#             "dynamic": body.type == "ACTIVE",
#             "shape": body.collision_shape,
#             "mass": body.mass,
#             "restitution": body.restitution,
#             "friction": body.friction,
#         })
#
# bpy.ops.export_scene.gltf(export_format="GLB",
#                           export_copyright="Gurakl Games",
#                           export_texcoords=True,
#                           export_normals=True,
#                           export_tangents=True,
#                           export_materials='$export_materials',
#                           export_colors=True,
#                           export_cameras=False,
#                           export_lights=True,
#                           export_extras=True,
#                           export_yup=False,
#                           export_apply=False,
#                           export_animations=False,
#                           export_skins=False,
#                           export_morph=False,
#                           filepath="$file_name.glb")
# # saving metadata
# with open("$file_name.meta", 'w') as outfile:
#     json.dump(metadata, outfile)""")
#     return __blender_script_template.substitute({
#         'file_name': dest_file_name,
#         'export_materials': 'NONE' if geometry_kind == 'terrain_chunk' else 'EXPORT'
#     })

