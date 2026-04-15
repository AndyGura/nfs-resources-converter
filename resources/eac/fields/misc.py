import math
from typing import Dict

from library.context import WriteContext
from library.read_blocks import IntegerBlock, CompoundBlock, SubByteCompoundBlock


class Point2D(CompoundBlock):

    @property
    def schema(self) -> Dict:
        schema = super().schema
        return {
            **schema,
            'block_description': 'Point in 2D space (x,y), where each coordinate is: '
                                 + schema['fields'][0]['schema']['block_description'] + (
                                     ', normalized' if self.normalized else ''
                                 ),
            'inline_description': True,
        }

    def __init__(self, child, normalized=False, **kwargs):
        self.normalized = normalized
        super().__init__(fields=[('x', child, {}),
                                 ('y', child, {})], **kwargs)

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        if self.normalized:
            length = math.sqrt(data['x'] ** 2 + data['y'] ** 2)
            if length == 0:
                data['y'] = 1.0
            elif length != 1:
                data['x'] /= length
                data['y'] /= length
        return super().write(data, ctx, name)


class Point3D(CompoundBlock):

    @property
    def schema(self) -> Dict:
        schema = super().schema
        return {
            **schema,
            'block_description': 'Point in 3D space (x,y,z), where each coordinate is: '
                                 + schema['fields'][0]['schema']['block_description'] + (
                                     ', normalized' if self.normalized else ''
                                 ),
            'inline_description': True,
        }

    def __init__(self, child, normalized=False, **kwargs):
        self.normalized = normalized
        super().__init__(fields=[('x', child, {}),
                                 ('y', child, {}),
                                 ('z', child, {})], **kwargs)

    def write(self, data, ctx: WriteContext = None, name: str = '') -> bytes:
        if self.normalized:
            length = math.sqrt(data['x'] ** 2 + data['y'] ** 2 + data['z'] ** 2)
            if length == 0:
                data['z'] = 1.0
            elif length != 1:
                data['x'] /= length
                data['y'] /= length
                data['z'] /= length
        return super().write(data, ctx, name)


class RGBBlock(CompoundBlock):

    @property
    def schema(self) -> Dict:
        return {
            **super().schema,
            'block_description': "Color RGB values",
            'inline_description': True,
        }

    def __init__(self, **kwargs):
        child = IntegerBlock(length=1, is_signed=False)
        super().__init__(fields=[('r', child, {}),
                                 ('g', child, {}),
                                 ('b', child, {})], **kwargs)


