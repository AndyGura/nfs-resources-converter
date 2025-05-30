from typing import Dict

from library.read_blocks import (BitFlagsBlock,
                                 DeclarativeCompoundBlock,
                                 IntegerBlock,
                                 BytesBlock,
                                 ArrayBlock,
                                 UTF8Block,
                                 SubByteArrayBlock,
                                 EnumByteBlock,
                                 EnumLookupDelegateBlock,
                                 FixedPointBlock)
from resources.eac.fields.misc import FenceType, Point3D
from resources.eac.fields.numbers import Nfs1Angle14, Nfs1Angle8, Nfs1TimeField


class RoadSplinePoint(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {**super().schema,
                'block_description': 'The description of one single point of road spline. Thank you jeff-1amstudios for'
                                     ' your [OpenNFS1](https://github.com/jeff-1amstudios/OpenNFS1) project'}

    class Fields(DeclarativeCompoundBlock.Fields):
        left_verge = (FixedPointBlock(length=1, fraction_bits=3),
                      {'description': 'The distance to the left edge of road. After this point the grip '
                                      'decreases'})
        right_verge = (FixedPointBlock(length=1, fraction_bits=3),
                       {'description': 'The distance to the right edge of road. After this point the grip '
                                       'decreases'})
        left_barrier = (FixedPointBlock(length=1, fraction_bits=3),
                        {'description': 'The distance to invisible wall on the left'})
        right_barrier = (FixedPointBlock(length=1, fraction_bits=3),
                         {'description': 'The distance to invisible wall on the right'})
        num_lanes = (SubByteArrayBlock(length=2, bits_per_value=4),
                     {'description': 'Amount of lanes. First number is amount of oncoming lanes, second number is '
                                     'amount of ongoing ones'})
        fence_flag = (SubByteArrayBlock(length=2, bits_per_value=4),
                      {'description': 'Flags whether there is fence or not. First number is fence on left side, '
                                      'second number is fence on right side. Used for physics simulation'})
        verge_slide = (SubByteArrayBlock(length=2, bits_per_value=4),
                       {'description': 'A slidiness of road areas between verge distance and barrier. First number for '
                                       'left verge, second number for right verge. Values above 3 cause unbearable slide '
                                       'in the game and make it impossible to return back to road. High values around '
                                       'maximum (15) cause lags and even crashes'})
        item_mode = (EnumByteBlock(enum_names=[(0, 'lane_split'),
                                               (1, 'default_0'),
                                               (2, 'lane_merge'),
                                               (3, 'default_1'),
                                               (4, 'tunnel'),
                                               (5, 'cobbled_road'),
                                               (7, 'right_tunnel_A9_A2'),
                                               # OpenNFS1: left wall appeared to move across the track - snapped back as we got closer
                                               (8, 'unk_cl3_forest'),
                                               (9, 'left_tunnel_A4_A7'),
                                               (11, 'unk_autumn_valley_tribunes'),
                                               (12, 'left_tunnel_A4_A8'),
                                               (13, 'left_tunnel_A5_A8'),
                                               (14, 'waterfall_audio_left_channel'),
                                               (15, 'waterfall_audio_right_channel'),
                                               (16, 'unk_al1_uphill'),
                                               (17, 'transtropolis_noise_audio'),  # OpenNFS1: water left channel
                                               (18, 'water_audio'),  # OpenNFS1: water right channel
                                               ]),
                     {'description': 'Modifier of this point. Affects terrain geometry and/or some gameplay features'})
        position = (Point3D(child=FixedPointBlock(length=4, fraction_bits=16, is_signed=True)),
                    {'description': 'Coordinates of this point in 3D space. The unit is meter'})
        slope = (Nfs1Angle14(),
                 {'description': 'Slope of the road at this point (angle if road goes up or down)'})
        slant = (Nfs1Angle14(),
                 {'description': 'Perpendicular angle of road'})
        orientation = (Nfs1Angle14(),
                       {'description': 'Rotation of road path, if view from the top. Equals to '
                                       'atan2(next_x - x, next_z - z)'})
        unk1 = (IntegerBlock(length=2, required_value=0),
                {'is_unknown': True})
        side_normal = (Point3D(child=FixedPointBlock(length=2, fraction_bits=16, is_signed=True)),
                       {'description': 'Side normal vector'})
        unk2 = (IntegerBlock(length=2, required_value=0),
                {'is_unknown': True})

    def update_orientations(self, read_data, next_spline_point):
        from math import atan2, cos, sin
        orientation = atan2(next_spline_point['position']['x'] - read_data['position']['x'],
                            next_spline_point['position']['z'] - read_data['position']['z'])
        read_data['orientation'] = orientation
        read_data['side_normal']['x'] = cos(orientation)
        read_data['side_normal']['z'] = -sin(orientation)


class ModelPropDescrData(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {**super().schema,
                'block_description': 'Map prop settings if it is a 3D model'}

    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (IntegerBlock(length=1),
                       {'description': 'An index of prop in the track FAM file'})
        resource_id_2 = (IntegerBlock(length=1),
                         {'description': 'Seems to always be equal to `resource_id`, except for one prop on map CL1, '
                                         'which is not used on map',
                          'programmatic_value': lambda ctx: ctx.data('resource_id')})
        unk0 = (FixedPointBlock(length=4, fraction_bits=16, required_value=1.5),
                {'is_unknown': True})
        unk1 = (FixedPointBlock(length=4, fraction_bits=16),
                {'is_unknown': True,
                 'programmatic_value': lambda _: 1.5,
                 'description': 'The purpose is unknown. Every single entry in TNFS files equals to 1.5 '
                                '(0x00_80_01_00) just like `unk0`, except for one prop on CL1, which has broken '
                                'texture palette and which is not used on the map anyways'})
        unk2 = (FixedPointBlock(length=4, fraction_bits=16, required_value=3),
                {'is_unknown': True})


class BitmapPropDescrData(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {**super().schema,
                'block_description': 'Map prop settings if it is a bitmap'}

    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (IntegerBlock(length=1),
                       {'description': 'Represents texture id. How to get texture name from this value [explained]'
                                       '(http://www.math.polytechnique.fr/cmat/auroux/nfs/nfsspecs.txt) well '
                                       'by Denis Auroux'})
        resource_id_2 = (IntegerBlock(length=1),
                         {'description': 'Oftenly equals to `resource_id`, but can be different'})
        width = (FixedPointBlock(length=4, fraction_bits=16, is_signed=True),
                 {'description': 'Width in meters'})
        frame_count = (IntegerBlock(length=1),
                       {'description': 'Frame amount for animated object. Ignored if flag `is_animated` not set'})
        animation_interval = (Nfs1TimeField(length=1),
                              {'description': 'Interval between animation frames in seconds'})
        unk0 = (IntegerBlock(length=1, is_signed=False),
                {'is_unknown': True})
        unk1 = (IntegerBlock(length=1, is_signed=False),
                {'is_unknown': True})
        height = (FixedPointBlock(length=4, fraction_bits=16, is_signed=True),
                  {'description': 'Height in meters'})


class TwoSidedBitmapPropDescrData(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {**super().schema,
                'block_description': 'Map prop settings if it is a two-sided bitmap (fake 3D model)'}

    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (IntegerBlock(length=1),
                       {'description': 'Represents texture id. How to get texture name from this value [explained]'
                                       '(http://www.math.polytechnique.fr/cmat/auroux/nfs/nfsspecs.txt) well '
                                       'by Denis Auroux'})
        resource_id_2 = (IntegerBlock(length=1),
                         {'description': 'Texture id of second sprite, rotated 90 degrees. Logic to determine texture '
                                         'name is the same as for resource_id'})
        width = (FixedPointBlock(length=4, fraction_bits=16, is_signed=True),
                 {'description': 'Width in meters'})
        width_2 = (FixedPointBlock(length=4, fraction_bits=16, is_signed=True),
                   {'description': 'Width in meters of second bitmap'})
        height = (FixedPointBlock(length=4, fraction_bits=16, is_signed=True),
                  {'description': 'Height in meters'})


class PropDescr(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {**super().schema,
                'block_description': 'The description of map prop: everything except terrain (road signs, '
                                     'buildings etc.) Thanks to jeff-1amstudios and his [OpenNFS1](https://github.com'
                                     '/jeff-1amstudios/OpenNFS1/blob/357fe6c3314a6f5bae47e243ca553c5491ecde79/OpenNFS1'
                                     '/Parsers/TriFile.cs#L202) project'}

    class Fields(DeclarativeCompoundBlock.Fields):
        flags = (BitFlagsBlock(flag_names=[(2, 'is_animated')]),
                 {'description': 'Different modes of prop'})
        type = (EnumByteBlock(enum_names=[(1, 'model'), (4, 'bitmap'), (6, 'two_sided_bitmap')]),
                {'description': 'Type of prop'})
        data = (EnumLookupDelegateBlock(enum_field='type',
                                        blocks=[ModelPropDescrData(),
                                                BitmapPropDescrData(),
                                                TwoSidedBitmapPropDescrData(),
                                                BytesBlock(length=14)]),
                {'description': 'Settings of the prop. Block class picked according to `type`'})


class MapProp(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {**super().schema,
                'block_description': 'The prop on the map. For instance: exactly the same road sign used 5 '
                                     'times on the map. In this case file will have 1 PropDescr for this road sign '
                                     'and 5 MapProps'}

    class Fields(DeclarativeCompoundBlock.Fields):
        road_point_idx = (IntegerBlock(length=4, is_signed=True),
                          {'description': 'Index of point of the road path spline, where prop is located. Sometimes '
                                          'has too big value, I skip those instances for now and it seems to look good.'
                                          ' Probably should consider this value to be 16-bit integer, having some '
                                          'unknown 16-integer as next field. Also, why it is '
                                          'signed?'})
        prop_descr_idx = (IntegerBlock(length=1),
                          {'description': 'Index of prop description, which should be used for this prop. '
                                          'Sometimes has too big value, I use object index % amount of prop '
                                          'descriptions for now and it seems to look good'})
        rotation = (Nfs1Angle8(),
                    {'description': 'Y-rotation, relative to rotation of referenced road spline vertex'})
        flags = (IntegerBlock(length=4),
                 {'is_unknown': True})
        position = (Point3D(child=FixedPointBlock(length=2, fraction_bits=8, is_signed=True)),
                    {'description': 'Position in 3D space, relative to position of referenced road spline vertex. '
                                    'The unit is meter'})


class TerrainEntry(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {**super().schema,
                'block_description': 'The terrain model around 4 spline points. It has good explanation in original '
                                     '[Denis Auroux NFS file specs](http://www.math.polytechnique.fr/cmat/auroux/nfs/'
                                     'nfsspecs.txt)'}

    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = UTF8Block(length=4, required_value='TRKD')
        block_length = IntegerBlock(length=4, is_signed=False)
        block_number = IntegerBlock(length=4, is_signed=False, required_value=0)
        unknown = (IntegerBlock(length=1, required_value=0),
                   {'is_unknown': True})
        fence = FenceType()
        texture_ids = (ArrayBlock(child=IntegerBlock(length=1), length=10),
                       {'description': 'Texture ids to be used for terrain'})
        rows = (ArrayBlock(
            child=ArrayBlock(child=Point3D(child=FixedPointBlock(length=2, fraction_bits=7, is_signed=True)),
                             length=11), length=4),
                {'description': 'Terrain vertex positions. The unit is meter'})


class AIEntry(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {**super().schema,
                'block_description': 'The record describing AI behavior at given terrain chunk'}

    class Fields(DeclarativeCompoundBlock.Fields):
        top_speed = (IntegerBlock(length=1),
                     {'description': 'Max speed among all AI drivers in m/s'})
        legal_speed = (IntegerBlock(length=1),
                       {'description': 'Minimum speed in m/s that makes cops start pursuit'})
        safe_speed = (IntegerBlock(length=1),
                      {'description': 'Max traffic speed in m/s. Oncoming traffic does not obey it'})


class TriMap(DeclarativeCompoundBlock):

    @property
    def schema(self) -> Dict:
        return {**super().schema,
            'custom_actions': [
                {
                    'method': 'reverse_track',
                    'title': 'Reverse track',
                    'description': 'Makes this track to go backwards',
                    'args': [],
                },
                {
                    'method': 'flatten_track',
                    'title': 'Flatten track',
                    'description': 'Makes track super flat: going forward without turns, slopes and slants',
                    'args': [],
                },
                {
                    'method': 'scale_track',
                    'title': 'Scale track length',
                    'description': 'Makes track shorter or longer by scaling it. Does not affect objects and terrain size',
                    'args': [{'id': 'scale', 'title': 'Scale', 'type': 'number'}],
                },
            ],
            'block_description': 'Map TRI file, represents terrain mesh, road itself, props locations etc.'}

    class Fields(DeclarativeCompoundBlock.Fields):
        resource_id = (IntegerBlock(length=4, required_value=0x11),
                       {'description': 'Resource ID'})
        loop_chunk = (IntegerBlock(length=2),
                      {'description': 'Index of chunk, on which game should use chunk #0 again. So for closed tracks '
                                      'this value should be equal to `num_chunks`, for open tracks it is 0'})
        num_chunks = (IntegerBlock(length=4),
                      {'description': 'number of terrain chunks (max 600)',
                       'programmatic_value': lambda ctx: len(ctx.data('terrain'))})
        unk0 = (IntegerBlock(length=2, required_value=6),
                {'is_unknown': True})
        position = (Point3D(child=FixedPointBlock(length=4, fraction_bits=16, is_signed=True)),
                    {'is_unknown': True})
        unknowns0 = (ArrayBlock(child=IntegerBlock(length=1, required_value=0), length=12),
                     {'is_unknown': True})
        chunks_size = (IntegerBlock(length=4),
                       {'description': 'Size of terrain array in bytes (num_chunks * 0x120)',
                        'programmatic_value': lambda ctx: len(ctx.data('terrain')) * 0x120})
        rail_tex_id = (IntegerBlock(length=4),
                       {'description': 'Do not know what is "railing". Doesn\'t look like a fence '
                                       'texture id, tested in TR1_001.FAM', 'is_unknown': True})
        lookup_table = (ArrayBlock(child=IntegerBlock(length=4), length=600),
                        {'description': '600 consequent numbers, each value is previous + 288. Looks like a space '
                                        'needed by the original NFS engine'})
        road_spline = (ArrayBlock(child=RoadSplinePoint(), length=2400),
                       {'description': "Road spline is a series of points in 3D space, located at the center of "
                                       "road. Around this spline the track terrain mesh is built. TRI always has "
                                       "2400 elements, however it uses only amount of vertices, equals to "
                                       "(num_chunks * 4), after them records filled with zeros. For opened "
                                       "tracks, finish line will be always located at spline point "
                                       "(num_chunks * 4 - 179)"})
        ai_info = ArrayBlock(child=AIEntry(), length=600)
        num_prop_descr = (IntegerBlock(length=4, is_signed=False),
                          {'programmatic_value': lambda ctx: len(ctx.data('prop_descr'))})
        num_props = (IntegerBlock(length=4, is_signed=False),
                     {'programmatic_value': lambda ctx: len(ctx.data('props'))})
        objs_hdr = UTF8Block(length=4, required_value='SJBO')
        unk1 = (IntegerBlock(length=4, required_value=0x428c),
                {'is_unknown': True})
        unk2 = (IntegerBlock(length=4, required_value=0),
                {'is_unknown': True})
        prop_descr = ArrayBlock(child=PropDescr(),
                                length=lambda ctx: ctx.data('num_prop_descr'))
        props = ArrayBlock(child=MapProp(),
                           length=lambda ctx: ctx.data('num_props'))
        terrain = ArrayBlock(child=TerrainEntry(),
                             length=lambda ctx: ctx.data('num_chunks'))

    def action_reverse_track(self, read_data):
        # FIXME lanes are a bit off: CY1.TRI now has both lanes oncoming, and racers drive on right verge. Traffic never appears
        # FIXME lane merge/split are broken. Is it possible to fix?
        # FIXME tunnel walls are broken. Is it possible to fix?
        # FIXME preserve 3D effect from two sided bitmaps (add math.pi to rotation, move base, switch side of side bitmap)
        # FIXME render order of props
        from math import cos, sin, pi, atan2
        def rotate_point(origin, point, angle):
            ox, oy = origin
            px, py = point
            qx = ox + cos(angle) * (px - ox) - sin(angle) * (py - oy)
            qy = oy + sin(angle) * (px - ox) + cos(angle) * (py - oy)
            return qx, qy

        road_spline_length = len(read_data['terrain']) * 4
        # start happens at 18th road spline vertex
        new_start_position = read_data['road_spline'][road_spline_length - 19]['position']
        new_start_next_position = read_data['road_spline'][road_spline_length - 20]['position']
        # Y - up; X - left; Z - forward;
        y_angle_to_rotate = pi - atan2(new_start_position['x'] - new_start_next_position['x'],
                                       new_start_position['z'] - new_start_next_position['z'])

        lane_effects = []
        start_x_road_offset = read_data['road_spline'][18]['position']['x']
        for i, vertex in enumerate(read_data['road_spline'][:road_spline_length]):
            # rotate so road at new start goes forward
            vertex['position']['z'], vertex['position']['x'] = rotate_point((0, 0),
                                                                            (vertex['position']['z'],
                                                                             vertex['position']['x']),
                                                                            y_angle_to_rotate)

        # translate so new start ==
        # -old_start.x (aligning car position for tracks, where road spline located at the side, like CY1)
        # 0,
        # 6.25 * 18 (average value for start position on original tracks)
        position_offset = [
            read_data['road_spline'][road_spline_length - 19]['position']['x'] + start_x_road_offset,
            read_data['road_spline'][road_spline_length - 19]['position']['y'],
            read_data['road_spline'][road_spline_length - 19]['position']['z'] - 6.25 * 18,
        ]
        for i, vertex in enumerate(read_data['road_spline'][:road_spline_length]):
            vertex['position']['x'] -= position_offset[0]
            vertex['position']['y'] -= position_offset[1]
            vertex['position']['z'] -= position_offset[2]
            # swap left and right
            (vertex['left_verge'], vertex['right_verge']) = (vertex['right_verge'], vertex['left_verge'])
            (vertex['left_barrier'], vertex['right_barrier']) = (vertex['right_barrier'], vertex['left_barrier'])
            # swap lanes
            vertex['num_lanes'] = [vertex['num_lanes'][1], vertex['num_lanes'][0]]
            vertex['lanes_unk'] = [vertex['lanes_unk'][1], vertex['lanes_unk'][0]]
            vertex['verge_slide'] = [vertex['verge_slide'][1], vertex['verge_slide'][0]]
            # change sign of slope/slant values
            vertex['slope'] = -vertex['slope']
            vertex['slant'] = -vertex['slant']
            vertex['side_normal']['y'] = -vertex['side_normal']['y']

            if vertex['item_mode'] == 'lane_split':
                vertex['item_mode'] = 'lane_merge'
                lane_effects.append(i)
            elif vertex['item_mode'] == 'lane_merge':
                vertex['item_mode'] = 'lane_split'
                # lane_effects.append(i)

        for index in lane_effects:
            (read_data['road_spline'][index]['item_mode'],
             read_data['road_spline'][index - 1]['item_mode']) = (
                read_data['road_spline'][index - 1]['item_mode'],
                read_data['road_spline'][index]['item_mode'])

        for chunk in read_data['terrain']:
            (chunk['fence']['has_left_fence'], chunk['fence']['has_right_fence']) = (
                chunk['fence']['has_right_fence'], chunk['fence']['has_left_fence'])
            chunk['texture_ids'] = chunk['texture_ids'][5:] + chunk['texture_ids'][:5]
            chunk['rows'] = chunk['rows'][::-1]
            for i in range(4):
                chunk['rows'][i] = [chunk['rows'][i][0]] + chunk['rows'][i][6:] + chunk['rows'][i][1:6]
                for j in range(11):
                    chunk['rows'][i][j]['z'], chunk['rows'][i][j]['x'] = rotate_point((0, 0),
                                                                                      (chunk['rows'][i][j]['z'],
                                                                                       chunk['rows'][i][j]['x']),
                                                                                      y_angle_to_rotate)

        amount_of_instances = [x['road_point_idx'] for x in read_data['props']].index(-1)
        for prop in read_data['props'][:amount_of_instances]:
            prop['road_point_idx'] = road_spline_length - 1 - prop['road_point_idx']
            prop['rotation'] += pi
            prop['position']['z'], prop['position']['x'] = rotate_point((0, 0),
                                                                        (prop['position']['z'],
                                                                         prop['position']['x']),
                                                                        y_angle_to_rotate)

        read_data['road_spline'] = (read_data['road_spline'][:road_spline_length][::-1]
                                    + read_data['road_spline'][road_spline_length:])
        read_data['ai_info'] = (read_data['ai_info'][:read_data['num_chunks']][::-1]
                                + read_data['ai_info'][read_data['num_chunks']:])
        read_data['terrain'] = read_data['terrain'][::-1]
        read_data['props'] = (read_data['props'][:amount_of_instances][::-1]
                              + read_data['props'][amount_of_instances:])
        # update rotations
        v_block = RoadSplinePoint()
        for i, vertex in enumerate(read_data['road_spline'][:road_spline_length]):
            v_block.update_orientations(vertex, read_data['road_spline'][i + 1 if i < road_spline_length else 0])

    def action_flatten_track(self, data):
        from math import cos, sin, pi
        for i, terrain_chunk in enumerate(data['terrain']):
            for j in range(4):
                terrain_chunk['rows'][j][0]['y'] = 0.0
                # rotate terrain mesh around first point
                angle = data['road_spline'][i * 4 + j]['orientation']
                cosine = cos(angle)
                sine = sin(angle)
                for k in range(1, 11):
                    terrain_chunk['rows'][j][k]['x'] -= terrain_chunk['rows'][j][0]['x']
                    terrain_chunk['rows'][j][k]['z'] -= terrain_chunk['rows'][j][0]['z']
                    x_new = terrain_chunk['rows'][j][k]['x'] * cosine - terrain_chunk['rows'][j][k]['z'] * sine
                    z_new = terrain_chunk['rows'][j][k]['x'] * sine + terrain_chunk['rows'][j][k]['z'] * cosine
                    terrain_chunk['rows'][j][k]['x'] = x_new + terrain_chunk['rows'][j][0]['x']
                    terrain_chunk['rows'][j][k]['z'] = z_new + terrain_chunk['rows'][j][0]['z']
        # fix props
        for prop in data['props']:
            road_vertex = data['road_spline'][prop['road_point_idx']]
            prop['rotation'] -= road_vertex['orientation']
            if prop['rotation'] < 0:
                prop['rotation'] += 2 * pi
            sine, cosine = sin(road_vertex['orientation']), cos(road_vertex['orientation'])
            prop['position']['x'], prop['position']['z'] = (
                prop['position']['x'] * cosine - prop['position']['z'] * sine,
                prop['position']['x'] * sine + prop['position']['z'] * cosine)

        for i, road_vertex in enumerate(data['road_spline'][:len(data['terrain']) * 4]):
            road_vertex['position']['x'] = road_vertex['position']['y'] = 0
            road_vertex['position']['z'] = i * 6.25
            road_vertex['slope'] = 0
            road_vertex['slant'] = 0
            road_vertex['side_normal']['y'] = 0
        # update rotations
        v_block = RoadSplinePoint()
        for i, vertex in enumerate(data['road_spline'][:len(data['terrain']) * 4]):
            v_block.update_orientations(vertex, data['road_spline'][i + 1 if i < len(data['terrain']) * 4 else 0])

    def action_scale_track(self, read_data, scale: float):
        scale = float(scale)
        for i, vertex in enumerate(read_data['road_spline']):
            vertex['position']['x'] *= scale
            vertex['position']['y'] *= scale
            vertex['position']['z'] *= scale
