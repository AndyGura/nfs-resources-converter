from typing import Dict

from library.read_blocks import (DeclarativeCompoundBlock,
                                 UTF8Block,
                                 IntegerBlock,
                                 ArrayBlock,
                                 BitFlagsBlock,
                                 FixedPointBlock,
                                 Padding)
from library.read_blocks.misc.value_validators import Eq
from resources.eac.fields.misc import Point3D


class GeoPolygon(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {**super().schema,
                'block_description': 'A single polygon of the mesh. Texture coordinates seem to be hardcoded in game:'
                                     'for triangles `[[0, 0], [1, 0], [1, 1]]` if "uv_flip" else '
                                     '`[[0, 1], [1, 1], [1, 0]]`, for quads `[[0, 1], [1, 1], [1, 0], [0, 0]]` if '
                                     '"uv_flip" else `[[0, 0], [1, 0], [1, 1], [0, 1]]`'}

    class Fields(DeclarativeCompoundBlock.Fields):
        mapping = (BitFlagsBlock(length=1,
                                 flag_names=[(0, 'is_triangle'),
                                             (1, 'uv_flip'),
                                             (2, 'flip_normal'),
                                             (4, 'double_sided')]),
                   {'description': 'Polygon properties. "is_triangle" means that 3th and 4th vertices in the polygon '
                                   'are the same, "uv_flip" changes texture coordinates, "flip normal" inverts normal '
                                   'vector of the polygon, "double-sided" makes polygon visible from the other side.'})
        unk0 = (IntegerBlock(length=3),
                {'is_unknown': True})
        vertex_indices = (ArrayBlock(child=IntegerBlock(length=1), length=4),
                          {'description': 'Indexes of vertices'})
        texture_name = (UTF8Block(length=4),
                        {'description': 'ID of texture from neighbouring QFS file'})


class GeoMesh(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {**super().schema,
                'block_description': 'A single mesh, can use multiple textures'}

    class Fields(DeclarativeCompoundBlock.Fields):
        num_vrtx = (IntegerBlock(length=4),
                    {'description': 'number of vertices in block'})
        num_plgn = (IntegerBlock(length=4),
                    {'description': 'number of polygons in block'})
        pos = (Point3D(child=FixedPointBlock(length=4, fraction_bits=16, is_signed=True)),
               {'description': 'position of part in 3d space. The unit is meter'})
        unk0 = (IntegerBlock(length=4),
                {'is_unknown': True})
        unk1 = (IntegerBlock(length=4),
                {'is_unknown': True})
        unk2 = (IntegerBlock(length=8, value_validator=Eq(0)),
                {'is_unknown': True})
        unk3 = (IntegerBlock(length=8, value_validator=Eq(1)),
                {'is_unknown': True})
        unk4 = (IntegerBlock(length=8, value_validator=Eq(1)),
                {'is_unknown': True})
        vertices = (ArrayBlock(length=lambda ctx: ctx.data('num_vrtx'),
                               child=Point3D(child=FixedPointBlock(length=2, fraction_bits=8, is_signed=True))),
                    {'description': 'Vertex coordinates. The unit is meter'})
        offset = (Padding(to=(lambda ctx: 52 + (ctx.data('num_vrtx') + 1) // 2 * 12,
                              '52 + ceil(num_vrtx/2)*12')),
                  {'description': 'Data offset, happens when `num_vrtx` is odd'})
        polygons = (ArrayBlock(length=lambda ctx: ctx.data('num_plgn'),
                               child=GeoPolygon()),
                    {'description': 'Array of mesh polygons'})


class GeoGeometry(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {**super().schema,
                'block_description': 'A set of 3D meshes, used for cars and props. Contains multiple meshes with '
                                     'high details, medium and low LOD-s'}

    class Fields(DeclarativeCompoundBlock.Fields):
        unk0 = (IntegerBlock(length=4),
                {'is_unknown': True})
        unk1 = (ArrayBlock(child=IntegerBlock(length=4), length=32),
                {'is_unknown': True})
        unk2 = (IntegerBlock(length=8),
                {'is_unknown': True})
        parts = (ArrayBlock(child=GeoMesh(), length=32),
                 {'description': 'Array of 32 body parts: 20 high poly, 3 medium poly, 3 low poly and 6 reserved '
                                 'spaces. Description of each of them:<br/>'
                                 '0: High-Poly Additional Body Part<br/>'
                                 '1: High-Poly Main Body Part<br/>'
                                 '2: High-Poly Ground Part<br/>'
                                 '3: High-Poly Front Part<br/>'
                                 '4: High-Poly Back Part<br/>'
                                 '5: High-Poly Left Side Part<br/>'
                                 '6: High-Poly Right Side Part<br/>'
                                 '7: High-Poly Additional Left Side Part<br/>'
                                 '8: High-Poly Additional Right Side Part<br/>'
                                 '9: High-Poly Spoiler Part<br/>'
                                 '10: High-Poly Additional Part<br/>'
                                 '11: High-Poly Backlights<br/>'
                                 '12: High-Poly Front Right Wheel<br/>'
                                 '13: High-Poly Front Right Wheel Part<br/>'
                                 '14: High-Poly Front Left Wheel<br/>'
                                 '15: High-Poly Front Left Wheel Part<br/>'
                                 '16: High-Poly Rear Right Wheel<br/>'
                                 '17: High-Poly Rear Right Wheel Part<br/>'
                                 '18: High-Poly Rear Left Wheel<br/>'
                                 '19: High-Poly Rear Left Wheel Part<br/>'
                                 '20: Medium-Poly Additional Body Part<br/>'
                                 '21: Medium-Poly Main Body Part<br/>'
                                 '22: Medium-Poly Ground Part<br/>'
                                 '23: Low-Poly Wheel Part<br/>'
                                 '24: Low-Poly Main Part<br/>'
                                 '25: Low-Poly Side Part<br/>'})

    def serializer_class(self):
        from serializers import GeoGeometrySerializer
        return GeoGeometrySerializer
