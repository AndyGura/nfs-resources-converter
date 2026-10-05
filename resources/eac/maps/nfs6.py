from typing import Dict

from library.read_blocks import (
    DeclarativeCompoundBlock,
    IntegerBlock,
    ArrayBlock,
    DecimalBlock,
    LengthPrefixedArrayBlock,
)
from library.read_blocks.strings import UTF8Block
from resources.eac.fields.misc import Point3D

# NFS6 (Hot Pursuit 2) track is a folder: "compNN.o" files are the track compartments (sections), "persist.viv"
# holds the textures of them ("track.fsh"), and every "levelNN" sub-folder is one race route. Its "drvpath.ini" lists
# compartments the route goes through, "levelG.o" and "level.fsh" are the route props (signs, barrels, spike strips,
# helicopter) and their textures, "level.dat" places them (not supported yet), and "aipaths.dat" is the road graph
# described here. See `EaglModel` in `resources/eac/geometries/nfs6.py` for the
# geometry files.


class Nfs6AiPathPoint(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {**super().schema, 'block_description': 'A point of the AI path'}

    class Fields(DeclarativeCompoundBlock.Fields):
        position = (Point3D(child=DecimalBlock(length=4)), {'description': 'Point position, Y is up'})
        left_width = (
            DecimalBlock(length=4),
            {'description': 'Distance from the path to the left edge of the drivable area (usually 10)'},
        )
        right_width = (
            DecimalBlock(length=4),
            {'description': 'Distance from the path to the right edge of the drivable area, negative (usually -10)'},
        )
        unk0 = (DecimalBlock(length=4), {'is_unknown': True, 'description': 'Values from -9 to 6, maybe road bank'})
        unk1 = (
            DecimalBlock(length=4),
            {'is_unknown': True, 'description': 'Values from 35 to 60, maybe recommended speed'},
        )


class Nfs6AiPath(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'A road between two graph nodes. Paths with the same start/end node positions '
            'are connected',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        name = (UTF8Block(length=16), {'description': 'Path name, e.g. "AI_center011"'})
        start_node = (IntegerBlock(length=4), {'description': 'Index of the graph node where the path starts'})
        end_node = (IntegerBlock(length=4), {'description': 'Index of the graph node where the path ends'})
        unk0 = (DecimalBlock(length=4), {'is_unknown': True, 'description': 'Always 44.703'})
        path_type = (
            IntegerBlock(length=4),
            {
                'is_unknown': True,
                'description': 'Path kind. Main road is 1, alternative roads and shortcuts have other values (2, 3, '
                '5, 8, 11)',
            },
        )
        points = (
            LengthPrefixedArrayBlock(length_block=IntegerBlock(length=4), child=Nfs6AiPathPoint()),
            {'description': 'Path points, from start node to end node'},
        )


class Nfs6AiPathGraph(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {**super().schema, 'block_description': 'A graph of paths'}

    class Fields(DeclarativeCompoundBlock.Fields):
        nodes = (
            LengthPrefixedArrayBlock(length_block=IntegerBlock(length=4), child=Point3D(child=DecimalBlock(length=4))),
            {'description': 'Graph nodes: start and end positions of every path'},
        )
        paths = (
            LengthPrefixedArrayBlock(length_block=IntegerBlock(length=4), child=Nfs6AiPath()),
            {'description': 'Paths'},
        )


class Nfs6AiPaths(DeclarativeCompoundBlock):
    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': 'NFS6 race route (levelNN/aipaths.dat): the road graph for AI cars and the flight '
            'paths of the police helicopter. Opening it shows the route in 3D: the compartments listed in '
            'drvpath.ini next to it ("compNN.o" files in the parent folder)',
        }

    class Fields(DeclarativeCompoundBlock.Fields):
        version = (IntegerBlock(length=4), {'is_unknown': True, 'description': 'Always 1'})
        road_paths = (Nfs6AiPathGraph(), {'description': 'Roads for AI cars'})
        helicopter_paths = (Nfs6AiPathGraph(), {'description': 'Flight paths of police helicopter'})

    def serializer_class(self):
        from serializers import Nfs6AiPathsSerializer

        return Nfs6AiPathsSerializer
