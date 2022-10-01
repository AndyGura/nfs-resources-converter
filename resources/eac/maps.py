from library.helpers.exceptions import BlockIntegrityException
from library.read_blocks.array import ArrayBlock
from library.read_blocks.atomic import BitFlagsBlock, IntegerBlock, EnumByteBlock, Utf8Block
from library.read_blocks.compound import CompoundBlock
from library.read_blocks.literal import LiteralBlock
from resources.eac.fields.misc import FenceType, Point3D_32, Point3D_16_7, Point3D_16
from resources.eac.fields.numbers import Nfs1Angle14, RationalNumber, Nfs1Angle8, Nfs1Angle16, Nfs1Interval


class RoadSplinePoint(CompoundBlock):
    block_description = 'The description of one single point of road spline. Thank you jeff-1amstudios for your ' \
                        'OpenNFS1 project: https://github.com/jeff-1amstudios/OpenNFS1'

    class Fields(CompoundBlock.Fields):
        left_verge_distance = RationalNumber(static_size=1, fraction_bits=3, is_signed=False,
                                             description='The distance to the left edge of road. After this point the '
                                                         'grip decreases')
        right_verge_distance = RationalNumber(static_size=1, fraction_bits=3, is_signed=False,
                                              description='The distance to the right edge of road. After this point the '
                                                          'grip decreases')
        left_barrier_distance = RationalNumber(static_size=1, fraction_bits=3, is_signed=False,
                                               description='The distance to invisible wall on the left')
        right_barrier_distance = RationalNumber(static_size=1, fraction_bits=3, is_signed=False,
                                                description='The distance to invisible wall on the right')
        unknowns0 = ArrayBlock(child=IntegerBlock(static_size=1), length=3)
        spline_item_mode = EnumByteBlock(enum_names=[(0, 'lane_split'),
                                                     (1, 'default_0'),
                                                     (2, 'lane_merge'),
                                                     (3, 'default_1'),
                                                     (4, 'tunnel'),
                                                     (5, 'cobbled_road'),
                                                     (7, 'right_tunnel_A2_A9'),
                                                     (12, 'left_tunnel_A9_A4'),
                                                     (13, 'left_tunnel_A9_A5'),
                                                     (14, 'waterfall_audio_left_channel'),
                                                     (15, 'waterfall_audio_right_channel'),
                                                     (17, 'transtropolis_noise_audio'),
                                                     (18, 'water_audio'),
                                                     ],
                                         description='Modifier of this point. Affects terrain geometry and/or some '
                                                     'gameplay features')
        position = Point3D_32(description='Coordinates of this point in 3D space')
        slope = Nfs1Angle14(description='Slope of the road at this point (angle if road goes up or down)')
        slant_a = Nfs1Angle14(description='Perpendicular angle of road')
        orientation = Nfs1Angle14(description='Rotation of road path, if view from the top')
        unknowns1 = ArrayBlock(child=IntegerBlock(static_size=1), length=2)
        orientation_y = Nfs1Angle16(description='Not quite sure about it. Denis Auroux gives more info about this '
                                                'http://www.math.polytechnique.fr/cmat/auroux/nfs/nfsspecs.txt')
        slant_b = Nfs1Angle16(description='has the same purpose as slant_a, but is a standard signed 16-bit value. '
                                          'Its value is positive for the left, negative for the right. The '
                                          'approximative relation between slant-A and slant-B is slant-B = -12.3 '
                                          'slant-A (remember that slant-A is 14-bit, though)')
        orientation_x = Nfs1Angle16(description='Not quite sure about it. Denis Auroux gives more info about this '
                                                'http://www.math.polytechnique.fr/cmat/auroux/nfs/nfsspecs.txt')
        unknowns2 = ArrayBlock(child=IntegerBlock(static_size=1), length=2)

        unknown_fields = ['unknowns0', 'unknowns1', 'unknowns2']


class ModelProxyObjectData(CompoundBlock):
    block_description = 'The proxy object settings if it is a 3D model'

    class Fields(CompoundBlock.Fields):
        resource_id = IntegerBlock(static_size=1,
                                   description='An index of prop in the track FAM file')
        unknowns = ArrayBlock(child=IntegerBlock(static_size=1, is_signed=False), length=13)

        unknown_fields = ['unknowns']


class BitmapProxyObjectData(CompoundBlock):
    block_description = 'The proxy object settings if it is a bitmap'

    class Fields(CompoundBlock.Fields):
        resource_id = IntegerBlock(static_size=1,
                                   description='Represents texture id. How to get texture name from this value '
                                               'explained well by Denis Auroux http://www.math.polytechnique.fr/'
                                               'cmat/auroux/nfs/nfsspecs.txt')
        proxy_number = IntegerBlock(static_size=1, is_signed=False,
                                    description='Seems to be always equal to own index * 4')
        width = RationalNumber(static_size=4, fraction_bits=16, is_signed=True, description='Width in meters')
        frame_count = IntegerBlock(static_size=1, description='Frame amount for animated object')
        animation_interval = Nfs1Interval(description='Interval between animation frames')
        unk0 = IntegerBlock(static_size=1, is_signed=False)
        unk1 = IntegerBlock(static_size=1, is_signed=False)
        height = RationalNumber(static_size=4, fraction_bits=16, is_signed=True, description='Height in meters')

        unknown_fields = ['unk0', 'unk1']


class TwoSidedBitmapProxyObjectData(CompoundBlock):
    block_description = 'The proxy object settings if it is a two-sided bitmap (fake 3D model)'

    class Fields(CompoundBlock.Fields):
        resource_id = IntegerBlock(static_size=1,
                                   description='Represents texture id. How to get texture name from this value '
                                               'explained well by Denis Auroux http://www.math.polytechnique.fr/'
                                               'cmat/auroux/nfs/nfsspecs.txt')
        resource_2_id = IntegerBlock(static_size=1,
                                     description='Texture id of second sprite, rotated 90 degrees. Logic to determine '
                                                 'texture name is the same as for resource_id')
        width = RationalNumber(static_size=4, fraction_bits=16, is_signed=True, description='Width in meters')
        width_2 = RationalNumber(static_size=4, fraction_bits=16, is_signed=True,
                                 description='Width in meters of second bitmap')
        height = RationalNumber(static_size=4, fraction_bits=16, is_signed=True, description='Height in meters')


class UnknownProxyObjectData(CompoundBlock):
    class Fields(CompoundBlock.Fields):
        unknowns = ArrayBlock(child=IntegerBlock(static_size=1, is_signed=False), length=14)

        unknown_fields = ['unknowns']


class ProxyObject(CompoundBlock):
    block_description = 'The description of map proxy object: everything except terrain (road signs, buildings etc.) ' \
                        'Thanks to jeff-1amstudios and his OpenNFS1 project: https://github.com/jeff-1amstudios/' \
                        'OpenNFS1/blob/357fe6c3314a6f5bae47e243ca553c5491ecde79/OpenNFS1/Parsers/TriFile.cs#L202'

    class Fields(CompoundBlock.Fields):
        flags = BitFlagsBlock(flag_names=[(2, 'is_animated')],
                              description='Different modes of proxy object')
        type = EnumByteBlock(enum_names=[(0, 'unk'), (1, 'model'), (4, 'bitmap'), (6, 'two_sided_bitmap')],
                             description='Type of proxy object')
        proxy_object_data = LiteralBlock(possible_resources=[ModelProxyObjectData(),
                                                             BitmapProxyObjectData(),
                                                             TwoSidedBitmapProxyObjectData(),
                                                             UnknownProxyObjectData()],
                                         description='Settings of the prop. Block class picked according to <type>')

    def _after_type_read(self, data, state, **kwargs):
        if not state.get('proxy_object_data'):
            state['proxy_object_data'] = {}
        if data['type'].value == 'model':
            state['proxy_object_data']['delegated_block'] = ModelProxyObjectData()
        elif data['type'].value == 'bitmap':
            state['proxy_object_data']['delegated_block'] = BitmapProxyObjectData()
        elif data['type'].value == 'two_sided_bitmap':
            state['proxy_object_data']['delegated_block'] = TwoSidedBitmapProxyObjectData()
        elif data['type'].value == 'unk':
            state['proxy_object_data']['delegated_block'] = UnknownProxyObjectData()
        else:
            raise BlockIntegrityException(f"Unknown proxy object type: {data['type'].value}")


class ProxyObjectInstance(CompoundBlock):
    block_description = 'The occurrence of proxy object. For instance: exactly the same road sign used 5 times on the' \
                        ' map. In this case file will have 1 ProxyObject for this road sign and 5 ProxyObjectInstances'

    class Fields(CompoundBlock.Fields):
        reference_road_spline_vertex = IntegerBlock(static_size=4, is_signed=True,
                                                    description='Sometimes has too big value, I skip those instances '
                                                                'for now and it seems to look good. Probably should '
                                                                'consider this value to be 16-bit integer, having some '
                                                                'unknown 16-integer as next field. Also, why it is '
                                                                'signed?')
        proxy_object_index = IntegerBlock(static_size=1, is_signed=False,
                                          description='Sometimes has too big value, I use object index % amount of '
                                                      'proxies for now and it seems to look good')
        rotation = Nfs1Angle8(description='Y-rotation, relative to rotation of referenced road spline vertex')
        flags = IntegerBlock(static_size=4)
        position = Point3D_16(description='Position in 3D space, relative to position of referenced road spline vertex')

        unknown_fields = ['flags']


class TerrainEntry(CompoundBlock):
    block_description = 'The terrain model around 4 spline points. It has good explanation in original Denis Auroux ' \
                        'NFS file specs: http://www.math.polytechnique.fr/cmat/auroux/nfs/nfsspecs.txt'

    class Fields(CompoundBlock.Fields):
        resource_id = Utf8Block(length=4, required_value='TRKD')
        block_length = IntegerBlock(static_size=4, is_signed=False)
        block_number = IntegerBlock(static_size=4, is_signed=False, required_value=0)
        unknown = IntegerBlock(static_size=1, required_value=0)
        fence = FenceType()
        texture_ids = ArrayBlock(child=IntegerBlock(static_size=1), length=10,
                                 description='Texture ids to be used for terrain')
        rows = ArrayBlock(child=ArrayBlock(child=Point3D_16_7(), length=11),
                          length=4, description='Terrain vertex positions')

        unknown_fields = ['unknown']


class AIEntry(CompoundBlock):
    block_description = 'The record describing AI behavior at given terrain chunk'

    class Fields(CompoundBlock.Fields):
        ai_speed = IntegerBlock(static_size=1, is_signed=False, description='Speed (m/h ?? ) of AI racer')
        unk = IntegerBlock(static_size=1, is_signed=False)
        traffic_speed = IntegerBlock(static_size=1, is_signed=False, description='Speed (m/h ?? ) of traffic car')

        unknown_fields = ['unk']


class TriMap(CompoundBlock):
    block_description = 'Map TRI file, represents terrain mesh, road itself, proxy object locations etc.'

    class Fields(CompoundBlock.Fields):
        resource_id = IntegerBlock(static_size=4, is_signed=False, required_value=0x11, description='Resource ID')
        num_segments = IntegerBlock(static_size=2, is_signed=False,
                                    description='0 for open tracks, num segments for closed')
        terrain_length = IntegerBlock(static_size=2, is_signed=False, description='number of terrain chunks (max 600)')
        unk0 = IntegerBlock(static_size=2, is_signed=False, required_value=0)
        unk1 = IntegerBlock(static_size=2, is_signed=False, required_value=6)
        position = Point3D_32()
        unknowns0 = ArrayBlock(child=IntegerBlock(static_size=1, required_value=0), length=12)
        terrain_block_size = IntegerBlock(static_size=4,
                                          description='Size of terrain array in bytes (terrain_length * 0x120)')
        railing_texture_id = IntegerBlock(static_size=4, is_signed=False,
                                          description='Do not know what is "railing". Doesn\'t look like a fence '
                                                      'texture id, tested in TR1_001.FAM')
        lookup_table = ArrayBlock(child=IntegerBlock(static_size=4, simplified=True), length=600,
                                  description='600 consequent numbers, each value is previous + 288. Looks like a space'
                                              ' needed by the original NFS engine')
        road_spline = ArrayBlock(child=RoadSplinePoint(), length=2400,
                                 description="Road spline is a series of points in 3D space, located at the center of "
                                             "road. Around this spline the track terrain mesh is built. TRI always has "
                                             "2400 elements, however it uses some amount of vertices, after them "
                                             "records filled with zeros")
        ai_info = ArrayBlock(child=AIEntry(), length=600)
        proxy_objects_count = IntegerBlock(static_size=4, is_signed=False)
        proxy_object_instances_count = IntegerBlock(static_size=4, is_signed=False)
        object_header_text = Utf8Block(length=4, required_value='SJBO')
        unk2 = IntegerBlock(static_size=4, is_signed=False, required_value=0x428c)
        unk3 = IntegerBlock(static_size=4, is_signed=False, required_value=0)
        proxy_objects = ArrayBlock(child=ProxyObject(), length_label='proxy_objects_count')
        proxy_object_instances = ArrayBlock(child=ProxyObjectInstance(), length_label='proxy_object_instances_count')
        terrain = ArrayBlock(child=TerrainEntry(), length_label="terrain_length")

        unknown_fields = ['unk0', 'unk1', 'unknowns0', 'railing_texture_id', 'position', 'unk2', 'unk3']

    def _after_terrain_length_read(self, data, state, **kwargs):
        if not state.get('terrain'):
            state['terrain'] = {}
        state['terrain']['length'] = data['terrain_length'].value

    def _after_proxy_object_instances_count_read(self, data, state, **kwargs):
        if not state.get('proxy_objects'):
            state['proxy_objects'] = {}
        state['proxy_objects']['length'] = data['proxy_objects_count'].value
        if not state.get('proxy_object_instances'):
            state['proxy_object_instances'] = {}
        state['proxy_object_instances']['length'] = data['proxy_object_instances_count'].value

    def list_custom_actions(self):
        return [*super().list_custom_actions(), {
        #     'method': 'reverse_track',
        #     'title': 'Reverse track',
        #     'description': 'Makes this track to go backwards',
        #     'args': [],
        # }, {
        #     'method': 'flatten_track',
        #     'title': 'Flatten track',
        #     'description': 'Makes track super flat: going forward without turns, slopes and slants',
        #     'args': [],
        # }, {
            'method': 'scale_track',
            'title': 'Scale track length',
            'description': 'Makes track shorter or longer by scaling it. Does not affect objects and terrain size',
            'args': [{'id': 'scale', 'title': 'Scale', 'type': 'number'}],
        }, ]

    # def action_reverse_track(self, read_data):
    #     # TODO
    #     pass
    #
    # def action_flatten_track(self, read_data):
    #     # TODO
    #     pass

    def action_scale_track(self, read_data, scale: float):
        for i, vertex in enumerate(read_data.road_spline):
            vertex.position.x.value *= scale
            vertex.position.y.value *= scale
            vertex.position.z.value *= scale
