import os
import tempfile
import unittest

from serializers.common.three_d import Scene, SubMesh, export_scenes


class _Settings:
    geometry__save_obj = True
    geometry__save_blend = False
    geometry__export_to_gg_web_engine = False


class TestExportScenes(unittest.TestCase):
    def test_scenes_with_same_file_names_should_go_to_their_directories(self):
        def scene(directory):
            mesh = SubMesh()
            mesh.name = 'mesh__tex'
            mesh.vertices = [[0, 0, 0], [1, 0, 0], [0, 1, 0]]
            mesh.vertex_uvs = [[0, 0], [1, 0], [0, 1]]
            mesh.polygons = [[0, 1, 2]]
            mesh.texture_id = 'tex'
            return Scene(
                name='body',
                sub_meshes=[mesh],
                obj_name='geometry',
                mtl_name='material',
                mtl_texture_names=['tex'],
                mtl_texture_path_func=lambda x: f'../../textures/{x}.png',
                dummies=[{'name': 'd', 'position': [0, 0, 0], 'properties': {}}],
                directory=directory,
            )

        with tempfile.TemporaryDirectory() as tmp:
            files = export_scenes([scene('a/'), scene('b/')], tmp + '/', _Settings())
            for directory in ['a', 'b']:
                for name in ['geometry.obj', 'geometry_extra.json', 'material.mtl']:
                    self.assertIn(os.path.join(tmp, directory, name), files)
                with open(os.path.join(tmp, directory, 'geometry.obj')) as f:
                    self.assertTrue(f.read().startswith('mtllib material.mtl'))
