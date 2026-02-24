from typing import Dict

from library.read_blocks import (DeclarativeCompoundBlock,
                                 UTF8Block,
                                 IntegerBlock,
                                 ArrayBlock,
                                 BytesBlock,
                                 BitFlagsBlock,
                                 FixedPointBlock)
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
        mapping = (BitFlagsBlock(flag_names=[(0, 'is_triangle'),
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
        offset = (BytesBlock(length=(lambda ctx: 0 if ctx.data('num_vrtx') % 2 == 0 else 6, '(num_vrtx % 2) ? 6 : 0')),
                  {'description': 'Data offset, happens when `num_vrtx` is odd'})
        polygons = (ArrayBlock(length=lambda ctx: ctx.data('num_plgn'),
                               child=GeoPolygon()),
                    {'description': 'Array of mesh polygons',
                     'custom_offset': '52 + ceil(num_vrtx/2)*12'})


class GeoGeometry(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {**super().schema,
                'block_description': 'A set of 3D meshes, used for cars and props. Contains multiple meshes with '
                                     'high details, medium and low LOD-s. Below `part_hp_x` is a high-poly part, '
                                     '`part_mp_x` and `part_lp_x` are medium and low-poly parts respectively'}

    class Fields(DeclarativeCompoundBlock.Fields):
        unk0 = (IntegerBlock(length=4),
                {'is_unknown': True})
        unk1 = (ArrayBlock(child=IntegerBlock(length=4), length=32),
                {'is_unknown': True})
        unk2 = (IntegerBlock(length=8),
                {'is_unknown': True})
        part_hp_0 = (GeoMesh(),
                     {'description': 'High-Poly Additional Body Part'})
        part_hp_1 = (GeoMesh(),
                     {'description': 'High-Poly Main Body Part'})
        part_hp_2 = (GeoMesh(),
                     {'description': 'High-Poly Ground Part'})
        part_hp_3 = (GeoMesh(),
                     {'description': 'High-Poly Front Part'})
        part_hp_4 = (GeoMesh(),
                     {'description': 'High-Poly Back Part'})
        part_hp_5 = (GeoMesh(),
                     {'description': 'High-Poly Left Side Part'})
        part_hp_6 = (GeoMesh(),
                     {'description': 'High-Poly Right Side Part'})
        part_hp_7 = (GeoMesh(),
                     {'description': 'High-Poly Additional Left Side Part'})
        part_hp_8 = (GeoMesh(),
                     {'description': 'High-Poly Additional Right Side Part'})
        part_hp_9 = (GeoMesh(),
                     {'description': 'High-Poly Spoiler Part'})
        part_hp_10 = (GeoMesh(),
                      {'description': 'High-Poly Additional Part'})
        part_hp_11 = (GeoMesh(),
                      {'description': 'High-Poly Backlights'})
        part_hp_12 = (GeoMesh(),
                      {'description': 'High-Poly Front Right Wheel'})
        part_hp_13 = (GeoMesh(),
                      {'description': 'High-Poly Front Right Wheel Part'})
        part_hp_14 = (GeoMesh(),
                      {'description': 'High-Poly Front Left Wheel'})
        part_hp_15 = (GeoMesh(),
                      {'description': 'High-Poly Front Left Wheel Part'})
        part_hp_16 = (GeoMesh(),
                      {'description': 'High-Poly Rear Right Wheel'})
        part_hp_17 = (GeoMesh(),
                      {'description': 'High-Poly Rear Right Wheel Part'})
        part_hp_18 = (GeoMesh(),
                      {'description': 'High-Poly Rear Left Wheel'})
        part_hp_19 = (GeoMesh(),
                      {'description': 'High-Poly Rear Left Wheel Part'})
        part_mp_0 = (GeoMesh(),
                     {'description': 'Medium-Poly Additional Body Part'})
        part_mp_1 = (GeoMesh(),
                     {'description': 'Medium-Poly Main Body Part'})
        part_mp_2 = (GeoMesh(),
                     {'description': 'Medium-Poly Ground Part'})
        part_lp_0 = (GeoMesh(),
                     {'description': 'Low-Poly Wheel Part'})
        part_lp_1 = (GeoMesh(),
                     {'description': 'Low-Poly Main Part'})
        part_lp_2 = (GeoMesh(),
                     {'description': 'Low-Poly Side Part'})
        part_res_0 = (GeoMesh(),
                      {'description': 'Reserved space for part'})
        part_res_1 = (GeoMesh(),
                      {'description': 'Reserved space for part'})
        part_res_2 = (GeoMesh(),
                      {'description': 'Reserved space for part'})
        part_res_3 = (GeoMesh(),
                      {'description': 'Reserved space for part'})
        part_res_4 = (GeoMesh(),
                      {'description': 'Reserved space for part'})
        part_res_5 = (GeoMesh(),
                      {'description': 'Reserved space for part'})

    def serializer_class(self):
        from serializers import GeoGeometrySerializer
        return GeoGeometrySerializer
