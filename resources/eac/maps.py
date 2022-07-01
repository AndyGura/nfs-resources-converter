from math import floor

from resources.basic.array_field import ArrayField
from resources.basic.atomic import BitFlagsField, IntegerField, EnumByteField, Utf8Field
from resources.basic.compound_block import CompoundBlock
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
        unknowns0 = ArrayField(child=IntegerField(static_size=1), length=3, is_unknown=True)
        spline_item_mode = EnumByteField(enum_names=[(0, 'lane_split'),
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
                                                     ], description='Modifier of this point')
        position = Point3D_32(description='Coordinates of this point in 3D space')
        slope = Nfs1Angle16(description='Slope of the road at this point')
        slant_a = Nfs1Angle16()
        orientation = Nfs1Angle16()
        unknowns1 = ArrayField(child=IntegerField(static_size=1), length=2, is_unknown=True)
        orientation_y = Nfs1Angle16()
        slant_b = Nfs1Angle16()
        orientation_x = Nfs1Angle16()
        unknowns2 = ArrayField(child=IntegerField(static_size=1), length=2, is_unknown=True)


class ProxyObject(CompoundBlock):
    block_description = 'The description of map proxy object: everything except terrain (road signs, buildings etc.) ' \
                        'Thanks to jeff-1amstudios and his OpenNFS1 project: https://github.com/jeff-1amstudios/' \
                        'OpenNFS1/blob/357fe6c3314a6f5bae47e243ca553c5491ecde79/OpenNFS1/Parsers/TriFile.cs#L202'

    class Fields(CompoundBlock.Fields):
        flags = BitFlagsField(flag_names=[(2, 'is_animated')],
                              description='Different modes of proxy object')
        type = EnumByteField(enum_names=[(1, 'model'), (4, 'bitmap'), (6, 'two_sided_bitmap')],
                             description='Type of proxy object')
        resource_id = IntegerField(static_size=1, description='Texture/model id')
        resource_2_id = IntegerField(static_size=1,
                                     description='Texture id of second sprite, rotated 90 degrees, in two-sided bitmap')
        width = RationalNumber(static_size=4, fraction_bits=16, is_signed=True)
        frame_count = IntegerField(static_size=1, description='Frame amount for animated object')
        unknowns0 = ArrayField(child=IntegerField(static_size=1), length=3, is_unknown=True,
                               description='Unknown, animation speed should be somewhere in it')
        height = RationalNumber(static_size=4, fraction_bits=16, is_signed=True)


class ProxyObjectInstance(CompoundBlock):
    block_description = 'The occurrence of proxy object. For instance: exactly the same road sign used 5 times on the' \
                        ' map. In this case file will have 1 ProxyObject for this road sign and 5 ProxyObjectInstances'

    class Fields(CompoundBlock.Fields):
        reference_road_spline_vertex = IntegerField(static_size=4, is_signed=True,
                                                    description='Sometimes has too big value, I skip those instances '
                                                                'for now and it seems to look good. Probably should '
                                                                'consider this value to be 16-bit integer, having some '
                                                                'unknown 16-integer as next field. Also, why it is '
                                                                'signed?')  # FIXME
        proxy_object_index = IntegerField(static_size=1, is_signed=False,
                                          description='Sometimes has too big value, I use object index % amount of '
                                                      'proxies for now and it seems to look good')  # FIXME
        rotation = Nfs1Angle8(description='Y-rotation, relative to rotation of referenced road spline vertex')
        flags = IntegerField(static_size=4, is_unknown=True)
        position = Point3D_16(description='Position in 3D space, relative to position of referenced road spline vertex')


class TerrainEntry(CompoundBlock):
    block_description = 'The terrain model around 4 spline points. It has good explanation in original Aurox NFS ' \
                        'file specs: http://www.math.polytechnique.fr/cmat/auroux/nfs/nfsspecs.txt'

    class Fields(CompoundBlock.Fields):
        id = Utf8Field(length=4, required_value='TRKD')
        block_length = IntegerField(static_size=4, is_signed=False)
        block_number = IntegerField(static_size=4, is_signed=False)
        unknown = IntegerField(static_size=1, is_unknown=True)
        fence = FenceType()
        texture_ids = ArrayField(child=IntegerField(static_size=1), length=10,
                                 description='Texture ids to be used for terrain')
        rows = ArrayField(child=ArrayField(child=Point3D_16_7(), length=11),
                          length=4, description='Terrain vertex positions')


class TriMap(CompoundBlock):
    block_description = 'Map TRI file, represents terrain mesh, road itself, proxy object locations etc.'

    class Fields(CompoundBlock.Fields):
        resource_id = IntegerField(static_size=4, is_signed=False, required_value=0x11)
        unknowns0 = ArrayField(child=IntegerField(static_size=1), length=8, is_unknown=True)
        position = Point3D_32(is_unknown=True)
        unknowns1 = ArrayField(child=IntegerField(static_size=1), length=12, is_unknown=True)
        scenery_data_length = IntegerField(static_size=4, is_unknown=True)
        unknowns2 = ArrayField(child=IntegerField(static_size=1), length=2404, is_unknown=True)
        road_spline = ArrayField(child=RoadSplinePoint(), length=2400,
                                 description="Road spline is a series of points in 3D space, located at the center of "
                                             "road. Around this spline the track terrain mesh is built. TRI always has "
                                             "2400 elements, however it uses some amount of vertices, after them "
                                             "records filled with zeros")
        unknowns3 = ArrayField(child=IntegerField(static_size=1), length=1800, is_unknown=True)
        proxy_objects_count = IntegerField(static_size=4, is_signed=False)
        proxy_object_instances_count = IntegerField(static_size=4, is_signed=False)
        object_header_text = Utf8Field(length=4, required_value='SJBO')
        unknowns4 = ArrayField(child=IntegerField(static_size=1), length=8, is_unknown=True)
        proxy_objects = ArrayField(child=ProxyObject(), length_label='proxy_objects_count')
        proxy_object_instances = ArrayField(child=ProxyObjectInstance(), length_label='proxy_object_instances_count')
        terrain = ArrayField(child=TerrainEntry(), length_label="spline_points_amount / 4")

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
