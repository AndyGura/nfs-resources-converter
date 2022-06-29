import json
import os
from collections import defaultdict
from io import BufferedReader, SEEK_CUR
from string import Template
from typing import List

import settings
from buffer_utils import read_int, read_utf_bytes, read_byte, read_signed_int, read_nfs1_float32_7, read_nfs1_float32_4
from parsers.resources.base import BaseResource
from parsers.resources.collections import ArchiveResource
from parsers.resources.common.blender_scripts import run_blender
from parsers.resources.common.meshes import SubMesh
from parsers.resources.read_block_wrapper import ReadBlockWrapper
from resources.eac.bitmaps import AnyBitmapResource


class Block:
    POLYGON = 0
    VERTEX_UV = 1
    TEXTURE_NAME = 2
    TEXTURE_NUMBER_MAP = 3
    UNK4 = 4
    UNK5 = 5
    LABEL = 6
    VERTEX = 7
    POLYGON_VERTEX_MAP = 8


class OripGeometryResource(BaseResource):

    @property
    def is_car(self):
        from parsers.resources.archives import WwwwArchive
        return isinstance(self.parent, WwwwArchive) and self.parent.name[-4:] == '.CFM'

    def read_float(self, buffer):
        return read_nfs1_float32_7(buffer) if self.is_car else read_nfs1_float32_4(buffer)

    def __init__(self):
        super().__init__()
        self._record_power: List[int] = [12, 8, 20, 20, 28, 12, 12, 12, 4]
        self._record_count: List[int] = [0] * 9
        self._offsets: List[int] = [0] * 9
        self.textures_archive: ArchiveResource = None
        self.sub_models = defaultdict(SubMesh)
        self.vertices_file_indices_map = defaultdict(lambda: dict())

    def _get_texture_name(self, buffer: BufferedReader, index: int) -> str:
        pointer = buffer.tell()
        buffer.seek(self._offsets[Block.TEXTURE_NAME] + index * self._record_power[Block.TEXTURE_NAME] + 8)
        name = read_utf_bytes(buffer, 4)
        buffer.seek(pointer)
        return name

    def _read_flags(self, buffer: BufferedReader, start_offset: int, length: int):
        buffer.seek(16, SEEK_CUR)
        self._record_count[Block.VERTEX] = read_int(buffer)
        buffer.seek(4, SEEK_CUR)
        self._offsets[Block.VERTEX] = start_offset + read_int(buffer)
        self._record_count[Block.VERTEX_UV] = read_int(buffer)
        self._offsets[Block.VERTEX_UV] = start_offset + read_int(buffer)
        self._record_count[Block.POLYGON] = read_int(buffer)
        self._offsets[Block.POLYGON] = start_offset + read_int(buffer)
        identifier = read_utf_bytes(buffer, 12)
        self._record_count[Block.TEXTURE_NAME] = read_int(buffer)
        self._offsets[Block.TEXTURE_NAME] = start_offset + read_int(buffer)
        self._record_count[Block.TEXTURE_NUMBER_MAP] = read_int(buffer)
        self._offsets[Block.TEXTURE_NUMBER_MAP] = start_offset + read_int(buffer)
        self._record_count[Block.UNK4] = read_int(buffer)
        self._offsets[Block.UNK4] = start_offset + read_int(buffer)
        self._offsets[Block.POLYGON_VERTEX_MAP] = start_offset + read_int(buffer)
        self._record_count[Block.POLYGON_VERTEX_MAP] = int(
            (length - self._offsets[Block.POLYGON_VERTEX_MAP] + start_offset) / self._record_power[
                Block.POLYGON_VERTEX_MAP])
        self._record_count[Block.UNK5] = read_int(buffer)
        self._offsets[Block.UNK5] = start_offset + read_int(buffer)
        self._record_count[Block.LABEL] = read_int(buffer)
        self._offsets[Block.LABEL] = start_offset + read_int(buffer)

    def read(self, buffer: BufferedReader, length: int, path: str = None) -> int:
        start_offset = buffer.tell()
        self._read_flags(buffer, start_offset, length)
        self.sub_models.clear()
        for i in range(0, self._record_count[Block.POLYGON]):
            buffer.seek(start_offset + i * self._record_power[Block.POLYGON] + 112)
            polygon_type = read_byte(buffer) & 255
            normal = read_byte(buffer)
            texture_id = self._get_texture_name(buffer, read_byte(buffer))
            sub_model = self.sub_models[texture_id]
            if not sub_model.name:
                sub_model.name = texture_id
                sub_model.texture_id = texture_id
            buffer.seek(1, SEEK_CUR)
            offset_3D = read_int(buffer)
            offset_2D = read_int(buffer)
            is_triangle = (polygon_type & (0xff >> 5)) == 3
            is_quad = (polygon_type & (0xff >> 5)) == 4
            if is_triangle:
                if normal in [17, 19]:
                    # two sided polygon
                    self._setup_polygon(sub_model, buffer, offset_3D, offset_2D, 0, 1, 2)
                    self._setup_polygon(sub_model, buffer, offset_3D, offset_2D, 0, 2, 1)
                elif normal in [18, 2, 3, 48, 50]:
                    self._setup_polygon(sub_model, buffer, offset_3D, offset_2D, 0, 1, 2, flip_texture=True)
                elif normal in [0, 1, 16]:
                    self._setup_polygon(sub_model, buffer, offset_3D, offset_2D, 0, 2, 1)
                else:
                    raise NotImplementedError(f'Unknown normal: {normal}, polygon type: {polygon_type}')
            elif is_quad:
                if normal in [17, 19]:
                    # two sided polygon
                    self._setup_polygon(sub_model, buffer, offset_3D, offset_2D, 0, 1, 3)
                    self._setup_polygon(sub_model, buffer, offset_3D, offset_2D, 1, 2, 3)
                    self._setup_polygon(sub_model, buffer, offset_3D, offset_2D, 0, 3, 1)
                    self._setup_polygon(sub_model, buffer, offset_3D, offset_2D, 1, 3, 2)
                elif normal in [18, 2, 3, 48, 50, 10, 6]:  # 10, 6 are unknown. Placed here for testing and looks good
                    self._setup_polygon(sub_model, buffer, offset_3D, offset_2D, 0, 1, 3, flip_texture=True)
                    self._setup_polygon(sub_model, buffer, offset_3D, offset_2D, 1, 2, 3, flip_texture=True)
                elif normal in [0, 1, 16]:
                    self._setup_polygon(sub_model, buffer, offset_3D, offset_2D, 0, 3, 1)
                    self._setup_polygon(sub_model, buffer, offset_3D, offset_2D, 1, 3, 2)
                else:
                    raise NotImplementedError(f'Unknown normal: {normal}, polygon type: {polygon_type}')
            elif polygon_type == 2:  # BURNT SIENNA prop. looks good without this polygon
                continue
            else:
                raise NotImplementedError(f'Unknown polygon: {polygon_type}')
        if self.is_car:
            if settings.geometry__skip_car_wheel_polygons:
                def is_model_nfs1_wheel(model: SubMesh) -> bool:
                    if model.name in ['tyr4', 'rty4']:  # TRAFFC.CFM
                        return True
                    if model.name == 'circ':  # wheel shadow
                        return True
                    if model.name == '\x00\x00\x00\x00':  # any other CFM
                        if len(model.polygons) == 8:
                            return True
                        if len(model.polygons) > 8:
                            # removing only wheel polygons (F512TR)
                            def is_polygon_wheel(polygon):
                                vertices = [model.vertices[i] for i in polygon]
                                is_match = True
                                wheel_key = None
                                for vert in vertices:
                                    key = (None
                                             if abs(vert[2]) < 0.1 or abs(vert[0]) < 0.1
                                             else f"{'f' if vert[2] > 0 else 'r'}{'l' if vert[0] < 0 else 'r'}")
                                    if not key or (wheel_key is not None and key != wheel_key):
                                        is_match = False
                                        break
                                    wheel_key = key
                                return is_match
                            model.polygons = [p for p in model.polygons if not is_polygon_wheel(p)]
                            removed_vertex_indices = [vi for vi in range(len(model.vertices)) if
                                                      vi not in [element for sublist in model.polygons for element in
                                                                 sublist]]
                            model.vertices = [v for (i, v) in enumerate(model.vertices) if
                                              i not in removed_vertex_indices]
                            model.vertex_uvs = [v for (i, v) in enumerate(model.vertex_uvs) if
                                                i not in removed_vertex_indices]
                            for removed_index in removed_vertex_indices[::-1]:
                                for j, p in enumerate(model.polygons):
                                    model.polygons[j] = [idx if idx <= removed_index else idx - 1 for idx in p]
                    return False

                self.sub_models = {k: v for k, v in self.sub_models.items() if not is_model_nfs1_wheel(v)}
        return length

    def save_converted(self, path: str):
        super().save_converted(path)
        if path[-1] != '/':
            path = path + '/'
        if not os.path.exists(path):
            os.makedirs(path)
        with open(f'{path}geometry.obj', 'w') as f:
            f.write('mtllib material.mtl')
            face_index_increment = 1
            for sub_model in self.sub_models.values():
                f.write(sub_model.to_obj(face_index_increment, True, self.textures_archive))
                face_index_increment += len(sub_model.vertices)
        with open(f'{path}material.mtl', 'w') as f:
            for texture in self.textures_archive.resources:
                if not isinstance(texture, ReadBlockWrapper) or not isinstance(texture.resource, AnyBitmapResource):
                    continue
                f.write(f"""\n\nnewmtl {texture.name}
Ka 1.000000 1.000000 1.000000
Kd 1.000000 1.000000 1.000000
Ks 0.000000 0.000000 0.000000
illum 1
Ns 0.000000
map_Kd assets/{texture.name}.png""")
        self.textures_archive.save_converted(os.path.join(path, 'assets/'))
        script = self.blender_script.substitute({'obj_file_path': 'geometry.obj', 'is_car': self.is_car})
        script += '\n' + settings.geometry__additional_exporter(f'{os.getcwd()}/{path}body',
                                                                'car' if self.is_car else 'prop')
        run_blender(path=path,
                    script=script,
                    out_blend_name=f'{os.getcwd()}/{path}body' if settings.geometry__save_blend else None)
        if not settings.geometry__save_obj:
            os.unlink(f'{path}material.mtl')
            os.unlink(f'{path}geometry.obj')

    def _setup_polygon(self, model: SubMesh, buffer: BufferedReader, offset_3D, offset_2D, *offsets,
                       flip_texture=False):
        model.polygons.append([self._setup_vertex(model, buffer, offset_3D + offset, offset_2D + offset, flip_texture)
                               for offset in offsets])

    def _setup_vertex(self, model: SubMesh, buffer: BufferedReader, index_3D, index_2D, flip_texture=False):
        try:
            return self.vertices_file_indices_map[model][index_3D]
        except KeyError:
            pass
        # new vertex creation
        buffer.seek(self._offsets[Block.POLYGON_VERTEX_MAP] + index_3D * self._record_power[Block.POLYGON_VERTEX_MAP])
        buffer.seek(self._offsets[Block.VERTEX] + read_int(buffer) * self._record_power[Block.VERTEX])
        # z inverted
        model.vertices.append([self.read_float(buffer), self.read_float(buffer), -self.read_float(buffer)])
        self.vertices_file_indices_map[model][index_3D] = len(model.vertices) - 1
        # setup texture coordinate
        buffer.seek(self._offsets[Block.POLYGON_VERTEX_MAP] + index_2D * self._record_power[Block.POLYGON_VERTEX_MAP])
        uv_vertex_index = read_int(buffer)
        if uv_vertex_index < self._record_count[Block.VERTEX_UV]:
            buffer.seek(self._offsets[Block.VERTEX_UV] + uv_vertex_index * self._record_power[Block.VERTEX_UV])
            model.vertex_uvs.append([read_signed_int(buffer) for _ in range(0, 2)])
        else:
            model.scaled_uvs.add(len(model.vertex_uvs))
            uv = [
                1 if len(model.vertex_uvs) % 4 > 1 else 0,
                1 if len(model.vertex_uvs) % 2 == 1 else 0
            ]
            if flip_texture:
                uv = [uv[1], uv[0]]
            model.vertex_uvs.append(uv)
        return self.vertices_file_indices_map[model][index_3D]

    blender_script = Template("""
import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.obj(filepath="$obj_file_path", use_image_search=True)
    """)
