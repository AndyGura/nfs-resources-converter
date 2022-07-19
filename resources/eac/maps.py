from math import floor

from library.read_blocks.array import ArrayBlock
from library.read_blocks.atomic import BitFlagsBlock, IntegerBlock, EnumByteBlock, Utf8Field
from library.read_blocks.compound import CompoundBlock
from resources.eac.fields.misc import FenceType, Point3D_32, Point3D_16_7, Point3D_16
from resources.eac.fields.numbers import Nfs1Angle16, RationalNumber, Nfs1Angle8


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
                                                     (1, 'default'),
                                                     (2, 'lane_merge'),
                                                     (4, 'tunnel'),
                                                     (5, 'cobbled_road'),
                                                     (7, 'right_tunnel_A2_A9'),
                                                     (12, 'left_tunnel_A9_A4'),
                                                     (13, 'left_tunnel_A9_A5'),
                                                     (14, 'waterfall_audio_left_channel'),
                                                     (15, 'waterfall_audio_right_channel'),
                                                     (18, 'water_audio'),
                                                     ],
                                         description='Modifier of this point. Affects terrain geometry and/or some '
                                                     'gameplay features')
        position = Point3D_32(description='Coordinates of this point in 3D space')
        slope = Nfs1Angle16(description='Slope of the road at this point (angle if road goes up or down)')
        slant_a = Nfs1Angle16(description='Perpendicular angle of road')
        orientation = Nfs1Angle16(description='Rotation of road path, if view from the top')
        unknowns1 = ArrayBlock(child=IntegerBlock(static_size=1), length=2)
        orientation_y = Nfs1Angle16(description='Not quite sure about it. Denis Auroux gives more info about this '
                                                'http://www.math.polytechnique.fr/cmat/auroux/nfs/nfsspecs.txt')
        slant_b = Nfs1Angle16(description='Not quite sure about it. Denis Auroux gives more info about this '
                                          'http://www.math.polytechnique.fr/cmat/auroux/nfs/nfsspecs.txt')
        orientation_x = Nfs1Angle16(description='Not quite sure about it. Denis Auroux gives more info about this '
                                                'http://www.math.polytechnique.fr/cmat/auroux/nfs/nfsspecs.txt')
        unknowns2 = ArrayBlock(child=IntegerBlock(static_size=1), length=2)
        
        unknown_fields = ['unknowns0', 'unknowns1', 'unknowns2']


class ProxyObject(CompoundBlock):
    block_description = 'The description of map proxy object: everything except terrain (road signs, buildings etc.) ' \
                        'Thanks to jeff-1amstudios and his OpenNFS1 project: https://github.com/jeff-1amstudios/' \
                        'OpenNFS1/blob/357fe6c3314a6f5bae47e243ca553c5491ecde79/OpenNFS1/Parsers/TriFile.cs#L202'

    class Fields(CompoundBlock.Fields):
        flags = BitFlagsBlock(flag_names=[(2, 'is_animated')],
                              description='Different modes of proxy object')
        type = EnumByteBlock(enum_names=[(1, 'model'), (4, 'bitmap'), (6, 'two_sided_bitmap')],
                             description='Type of proxy object')
        resource_id = IntegerBlock(static_size=1,
                                   description='Texture/model id. For 3D prop is an index of prop in the track FAM '
                                               'file, for 2D represents texture id. How to get texture name from this '
                                               'value explained well by Denis Auroux http://www.math.polytechnique.fr/'
                                               'cmat/auroux/nfs/nfsspecs.txt')
        resource_2_id = IntegerBlock(static_size=1,
                                     description='Texture id of second sprite, rotated 90 degrees, in two-sided bitmap.'
                                                 ' Logic to determine texture name is the same as for resource_id. '
                                                 'Applicable for 2D prop with type two_sided_bitmap')
        width = RationalNumber(static_size=4, fraction_bits=16, is_signed=True, description='Width in meters')
        frame_count = IntegerBlock(static_size=1, description='Frame amount for animated object')
        unknowns0 = ArrayBlock(child=IntegerBlock(static_size=1), length=3,
                               description='Unknown, animation speed should be somewhere in it')
        height = RationalNumber(static_size=4, fraction_bits=16, is_signed=True,
                                description='Height in meters, applicable for 2D props')

        unknown_fields = ['unknowns0']


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
        resource_id = Utf8Field(length=4, required_value='TRKD')
        block_length = IntegerBlock(static_size=4, is_signed=False)
        block_number = IntegerBlock(static_size=4, is_signed=False)
        unknown = IntegerBlock(static_size=1)
        fence = FenceType()
        texture_ids = ArrayBlock(child=IntegerBlock(static_size=1), length=10,
                                 description='Texture ids to be used for terrain')
        rows = ArrayBlock(child=ArrayBlock(child=Point3D_16_7(), length=11),
                          length=4, description='Terrain vertex positions')

        unknown_fields = ['unknown']


class TriMap(CompoundBlock):
    block_description = 'Map TRI file, represents terrain mesh, road itself, proxy object locations etc.'

    class Fields(CompoundBlock.Fields):
        resource_id = IntegerBlock(static_size=4, is_signed=False, required_value=0x11, description='Resource ID')
        unknowns0 = ArrayBlock(child=IntegerBlock(static_size=1), length=8)
        position = Point3D_32()
        unknowns1 = ArrayBlock(child=IntegerBlock(static_size=1), length=12)
        scenery_data_length = IntegerBlock(static_size=4)
        unknowns2 = ArrayBlock(child=IntegerBlock(static_size=1), length=2404)
        road_spline = ArrayBlock(child=RoadSplinePoint(), length=2400,
                                 description="Road spline is a series of points in 3D space, located at the center of "
                                             "road. Around this spline the track terrain mesh is built. TRI always has "
                                             "2400 elements, however it uses some amount of vertices, after them "
                                             "records filled with zeros")
        unknowns3 = ArrayBlock(child=IntegerBlock(static_size=1), length=1800)
        proxy_objects_count = IntegerBlock(static_size=4, is_signed=False)
        proxy_object_instances_count = IntegerBlock(static_size=4, is_signed=False)
        object_header_text = Utf8Field(length=4, required_value='SJBO')
        unknowns4 = ArrayBlock(child=IntegerBlock(static_size=1), length=8)
        proxy_objects = ArrayBlock(child=ProxyObject(), length_label='proxy_objects_count')
        proxy_object_instances = ArrayBlock(child=ProxyObjectInstance(), length_label='proxy_object_instances_count')
        terrain = ArrayBlock(child=TerrainEntry(), length_label="spline_points_amount / 4")

        unknown_fields = ['unknowns0', 'position', 'unknowns1', 'scenery_data_length', 'unknowns2', 'unknowns3', 
                          'unknowns4']

    def _after_road_spline_read(self, data, **kwargs):
        data['road_spline'] = data['road_spline'][:next(i for i, x in enumerate(data['road_spline']) if x.position.x
                                                        == x.position.y
                                                        == x.position.z
                                                        == x.left_verge_distance
                                                        == x.right_verge_distance
                                                        == x.left_barrier_distance
                                                        == x.right_barrier_distance
                                                        == 0)]
        self.instance_fields_map['terrain'].length = floor(len(data['road_spline']) / 4)

    def _after_proxy_object_instances_count_read(self, data, **kwargs):
        self.instance_fields_map['proxy_objects'].length = data['proxy_objects_count']
        self.instance_fields_map['proxy_object_instances'].length = data['proxy_object_instances_count']
