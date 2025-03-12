from typing import Dict

from library.read_blocks import (DeclarativeCompoundBlock,
                                 IntegerBlock,
                                 BytesBlock,
                                 ArrayBlock, CompoundBlock, EnumByteBlock, DelegateBlock, SkipBlock,
                                 LengthPrefixedArrayBlock)
from resources.eac.fields.misc import Point3D


class FrdPositionBlock(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        polygon = IntegerBlock(length=2, is_signed=False)
        nPolygons = IntegerBlock(length=1, is_signed=False)
        unk = IntegerBlock(length=1, is_signed=False)
        extraNeighbor1 = IntegerBlock(length=2, is_signed=False)
        extraNeighbor2 = IntegerBlock(length=2, is_signed=False)


class FrdBlock(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        center = Point3D(child_length=4, fraction_bits=24)
        bounds = (ArrayBlock(child=Point3D(child_length=4, fraction_bits=24), length=4),
                  {'description': 'Block bounding rectangle'})
        num_vertices = (IntegerBlock(length=4, is_signed=False),
                        {'description': 'Number of vertices',
                         'programmatic_value': lambda ctx: len(ctx.data('vertices'))})
        num_vertices_high = (IntegerBlock(length=4, is_signed=False),
                             {'description': 'Number of high-res vertices'})
        num_vertices_low = (IntegerBlock(length=4, is_signed=False),
                            {'description': 'Number of low-res vertices'})
        num_vertices_med = (IntegerBlock(length=4, is_signed=False),
                            {'description': 'Number of medium-res vertices'})
        num_vertices_dup = (IntegerBlock(length=4, is_signed=False),
                            {'is_unknown': True,
                             'programmatic_value': lambda ctx: len(ctx.data('vertices'))})
        num_vertices_obj = (IntegerBlock(length=4, is_signed=False),
                            {'is_unknown': True})
        vertices = (ArrayBlock(child=Point3D(child_length=4, fraction_bits=24),
                               length=lambda ctx: ctx.data('num_vertices')),
                    {'description': 'Vertices'})
        vertex_shading = (ArrayBlock(child=IntegerBlock(length=4, is_signed=False),
                                     length=lambda ctx: ctx.data('num_vertices')),
                          {'is_unknown': True})
        neighbour_data = (ArrayBlock(child=IntegerBlock(length=2, is_signed=False),
                                     length=2 * 0x12C),
                          {'is_unknown': True})
        nStartPos = (IntegerBlock(length=4, is_signed=False),
                     {'is_unknown': True})
        nPositions = (IntegerBlock(length=4, is_signed=False),
                      {'is_unknown': True,
                       'programmatic_value': lambda ctx: len(ctx.data('positions'))})
        nPolygons = (IntegerBlock(length=4, is_signed=False),
                     {'is_unknown': True,
                      'programmatic_value': lambda ctx: len(ctx.data('polyData'))})
        nVRoad = (IntegerBlock(length=4, is_signed=False),
                  {'is_unknown': True,
                   'programmatic_value': lambda ctx: len(ctx.data('vroadData'))})
        nXobj = (IntegerBlock(length=4, is_signed=False),
                 {'is_unknown': True,
                  'programmatic_value': lambda ctx: len(ctx.data('xobj'))})
        nPolyobj = (IntegerBlock(length=4, is_signed=False),
                    {'is_unknown': True,
                     'programmatic_value': lambda ctx: len(ctx.data('polyObj'))})
        nSoundsrc = (IntegerBlock(length=4, is_signed=False),
                     {'is_unknown': True,
                      'programmatic_value': lambda ctx: len(ctx.data('soundsrc'))})
        nLightsrc = (IntegerBlock(length=4, is_signed=False),
                     {'is_unknown': True,
                      'programmatic_value': lambda ctx: len(ctx.data('lightsrc'))})
        positions = (ArrayBlock(child=FrdPositionBlock(), length=lambda ctx: ctx.data('nPositions')),
                     {'is_unknown': True})
        polyData = (ArrayBlock(child=CompoundBlock(fields=[
            ('vroadEntry', IntegerBlock(length=1, is_signed=False), {}),
            ('flags', IntegerBlock(length=1, is_signed=False), {}),
            ('unk', BytesBlock(length=6), {}),
        ]), length=lambda ctx: ctx.data('nPolygons')),
                    {'is_unknown': True})
        vroadData = (ArrayBlock(child=CompoundBlock(fields=[
            ('normal', Point3D(child_length=2, fraction_bits=16, normalized=True), {}),
            ('forward', Point3D(child_length=2, fraction_bits=16, normalized=True), {}),
        ]), length=lambda ctx: ctx.data('nVRoad')),
                     {'is_unknown': True})
        xobj = (ArrayBlock(child=BytesBlock(length=20), length=lambda ctx: ctx.data('nXobj')),
                {'is_unknown': True})
        polyObj = (ArrayBlock(child=BytesBlock(length=20), length=lambda ctx: ctx.data('nPolyobj')),
                   {'is_unknown': True})
        soundsrc = (ArrayBlock(child=BytesBlock(length=16), length=lambda ctx: ctx.data('nSoundsrc')),
                    {'is_unknown': True})
        lightsrc = (ArrayBlock(child=BytesBlock(length=16), length=lambda ctx: ctx.data('nLightsrc')),
                    {'is_unknown': True})


class FrdPolygonRecord(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        vertices = ArrayBlock(child=IntegerBlock(length=2), length=4)
        tex_id = IntegerBlock(length=2)
        tex_flags = IntegerBlock(length=2)
        flags = IntegerBlock(length=1)
        unk = IntegerBlock(length=1)


class FrdPolyBlockInner(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        sz = IntegerBlock(length=4)
        data = DelegateBlock(possible_blocks=[LengthPrefixedArrayBlock(length_block=IntegerBlock(length=4),
                                                                       child=FrdPolygonRecord()),
                                              SkipBlock()],
                             choice_index=lambda ctx, **_: (
                                 0 if ctx.data('sz') != 0
                                 else 1))


class BBBB(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        type = IntegerBlock(length=4, is_signed=False)
        data = DelegateBlock(possible_blocks=[LengthPrefixedArrayBlock(length_block=IntegerBlock(length=4),
                                                                       child=FrdPolygonRecord()),
                                              SkipBlock()],
                             choice_index=lambda ctx, **_: (
                                 0 if ctx.data('type') == 1
                                 else 1))


class AAAA(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        n1 = IntegerBlock(length=4)
        data = DelegateBlock(possible_blocks=[LengthPrefixedArrayBlock(child=BBBB(),
                                                                       length_block=IntegerBlock(length=4)),
                                              SkipBlock()],
                             choice_index=lambda ctx, **_: (
                                 0 if ctx.data('n1') > 0
                                 else 1))


class FrdPolyBlock(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        a = ArrayBlock(child=FrdPolyBlockInner(), length=7)
        b = ArrayBlock(child=AAAA(), length=4)


class ExtraObjectData(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        crosstype = IntegerBlock(length=4)
        crossno = IntegerBlock(length=4)
        unk0 = IntegerBlock(length=4)
        data = DelegateBlock(possible_blocks=[
            CompoundBlock(fields=[
                ('ptRef', Point3D(child_length=4, fraction_bits=24), {}),
                ('AnimMemory', IntegerBlock(length=4), {}),
            ]),
            CompoundBlock(fields=[
                ('unknown3', BytesBlock(length=18), {}),
                ('type3', IntegerBlock(length=1, required_value=3), {}),
                ('objno', IntegerBlock(length=1), {}),
                ('nAnimLength', IntegerBlock(length=2), {}),
                ('AnimDelay', IntegerBlock(length=2), {}),
                ('animData', ArrayBlock(child=CompoundBlock(fields=[
                    ('pt', Point3D(child_length=4, fraction_bits=24), {}),
                    ('od', ArrayBlock(child=IntegerBlock(length=2), length=4), {}),
                ]),
                    length=lambda ctx: ctx.data('nAnimLength')), {}),
            ])
        ], choice_index=lambda ctx, **_: 0 if ctx.data('crosstype') == 4 else 1)
        vertices = LengthPrefixedArrayBlock(length_block=IntegerBlock(length=4),
                                            child=Point3D(child_length=4, fraction_bits=24))
        vertShading = ArrayBlock(child=IntegerBlock(length=4),
                                 length=lambda ctx: len(ctx.data('vertices')))
        polygons = LengthPrefixedArrayBlock(length_block=IntegerBlock(length=4), child=FrdPolygonRecord())


class TextureBlock(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        width = (IntegerBlock(length=2, is_signed=False),
                 {'description': 'Texture width'})
        height = (IntegerBlock(length=2, is_signed=False),
                  {'description': 'Texture height'})
        unk0 = (IntegerBlock(length=4),
                {'description': 'Blending related, hometown covered bridges godrays',
                 'is_unknown': True})
        # TODO float
        corners = (ArrayBlock(child=IntegerBlock(length=4), length=8),
                   {'description': '4x planar coordinates == tiling?',
                    'is_unknown': True})
        unk1 = (IntegerBlock(length=4),
                {'is_unknown': True})
        is_lane = (EnumByteBlock(enum_names=[(0, 'default'),
                                             (1, 'lane'),
                                             ]),
                   {'description': '1 if not a real texture (lane), 0 usually',
                    'is_unknown': True})
        texture_id = (IntegerBlock(length=2, is_signed=False),
                      {'description': 'index in QFS file'})


class FrdMap(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {**super().schema,
                'block_description': 'Main track file'}

    class Fields(DeclarativeCompoundBlock.Fields):
        unk = (BytesBlock(length=28),
               {'description': 'Unknown header',
                'is_unknown': True})
        num_blocks = (IntegerBlock(length=4, is_signed=False),
                      {'description': 'Number of blocks',
                       'programmatic_value': lambda ctx: len(ctx.data('blocks')) - 1})
        blocks = ArrayBlock(child=FrdBlock(),
                            length=lambda ctx: ctx.data('num_blocks') + 1)
        polygon_blocks = ArrayBlock(child=FrdPolyBlock(),
                                    length=lambda ctx: ctx.data('num_blocks') + 1)

        extraobject_blocks = ArrayBlock(child=LengthPrefixedArrayBlock(child=ExtraObjectData(),
                                                                       length_block=IntegerBlock(length=4)),
                                        length=lambda ctx: 4 * (ctx.data('num_blocks') + 1))
        texture_blocks = LengthPrefixedArrayBlock(child=TextureBlock(), length_block=IntegerBlock(length=4))
