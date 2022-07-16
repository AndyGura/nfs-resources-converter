import json
from io import BufferedReader

from buffer_utils import read_utf_bytes
from parsers.resources.base import BaseResource
from parsers.resources.collections import ArchiveResource


class BinaryResource(BaseResource):

    def __init__(self, id=None, length=None, save_binary_file=True):
        super().__init__()
        self.id = id
        self.length = length
        self.save_binary_file = save_binary_file

    def read(self, buffer: BufferedReader, length: int, path: str = None) -> int:
        if self.length is not None:
            length = min(length, self.length)
        self.bytes = buffer.read(length)
        return length

    def save_converted(self, path: str):
        super().save_converted(path)
        if self.save_binary_file:
            if self.id:
                path = f'{path}__{hex(self.id)}'
            with open(f'{path}.bin', 'w+b') as file:
                file.write(self.bytes)


class JsonOutputResource:
    dictionary = dict()

    def save_converted(self, path: str):
        with open(f'{path}.json', 'w') as file:
            file.write(json.dumps(self.dictionary))


class TextResource(BaseResource):

    def read(self, buffer: BufferedReader, length: int, path: str = None) -> int:
        self.text = read_utf_bytes(buffer, length)
        return length

    def save_converted(self, path: str):
        super().save_converted(path)
        with open(f'{path}.txt', 'w') as file:
            file.write(self.text)


class DashDeclarationResource(JsonOutputResource, TextResource):
    def read(self, buffer: BufferedReader, length: int, path: str = None) -> int:
        self.dictionary = {}
        length_read = super().read(buffer, length, path)
        values = self.text.split('\n')
        current_key = None
        current_key_ended = True
        for value in values:
            if value.startswith('#'):
                if not current_key_ended:
                    raise Exception(f'Unexpected new key {value}. Last key not finished')
                current_key = value[1:]
                current_key_ended = False
                continue
            if value == '':
                if not self.dictionary.get(current_key):
                    self.dictionary[current_key] = []
                current_key_ended = True
                continue
            if not current_key:
                raise Exception(f'Cannot parse value {value}. Unknown key')
            if self.dictionary.get(current_key) is not None:
                if current_key_ended:
                    self.dictionary[current_key].append([value])
                    current_key_ended = False
                else:
                    self.dictionary[current_key][-1].append(value)
            else:
                value = value.split(' ')
                value = value[0] if len(value) == 1 else value
                self.dictionary[current_key] = value if not current_key_ended else [value]
        return length_read


class Nfs1MapInfo(DashDeclarationResource):
    @property
    def ring_height(self) -> int:
        return int(self.dictionary.get('ring height'))

    @property
    def ring_y(self) -> int:
        return int(self.dictionary.get('ring y offset (bigger places horizon further down)'))


def nfs1_panorama_to_spherical(track_id: str, file_name: str, out_file_name: str):
    from PIL import Image, ImageOps
    from numpy import average
    source = Image.open(file_name)

    out_half_width = 1024
    out_half_height = int(out_half_width / 2)

    scale_x = out_half_width / source.size[0]
    mirror_x = track_id in ['TR3', 'TR7']
    # It is a mystery how NFS decides how to position horizon. I tried everything in {track_id}INFO files,
    # but no stable correlations detected. NFS horizon is not a sphere, it is a separate 2D layer under 3D stage,
    # so output sky texture is approximate for FOV == 65
    scale_y = 2.12
    pos_y = 0
    if track_id in ['TR3', 'TR4']:
        scale_y = 1
    elif track_id == 'TR1':
        scale_y = 1.15
    elif track_id == 'TR2':
        scale_y = 0.86
    elif track_id == 'TR6':
        scale_y = 2.2
    if track_id == 'AL1':
        pos_y = 351
    elif track_id == 'AL2':
        pos_y = 336
    elif track_id == 'AL3':
        pos_y = 365
    elif track_id == 'CL1':
        pos_y = 375
    elif track_id == 'CL2':
        pos_y = 349
    elif track_id == 'CL3':
        pos_y = 374
    elif track_id == 'CY1':
        pos_y = 328
    elif track_id == 'CY2':
        pos_y = 294
    elif track_id == 'CY3':
        pos_y = 343
    elif track_id == 'TR1':
        pos_y = 324
    elif track_id == 'TR2':
        pos_y = 308
    elif track_id == 'TR3':
        pos_y = 367
    elif track_id == 'TR6':
        pos_y = 369
    elif track_id == 'TR7':
        pos_y = 342
    elif track_id == 'TR4':
        pos_y = 300

    scale_y = scale_y * out_half_width / 1024
    pos_y = int(pos_y * out_half_width / 1024)

    source_scaled = source.resize((int(source.size[0] * scale_x), int(source.size[1] * scale_y)), Image.ANTIALIAS)

    # INFO files have some values for top and bottom color, but I don't understand what exactly colors do they mean
    top_line_color = tuple([int(x)
                            for x in average(average(source.crop((0, 0, source.size[0], 1)), axis=0), axis=0)])
    bottom_line_color = tuple([int(x)
                               for x in average(average(source.crop((0,
                                                                     source.size[1] - 1,
                                                                     source.size[0],
                                                                     source.size[1])), axis=0), axis=0)])

    spherical = Image.new(source_scaled.mode, (out_half_width * 2, out_half_height * 2), 0xff000000)
    spherical.paste(top_line_color, [0, 0,
                                     spherical.size[0], int(pos_y + source_scaled.size[1] / 2)])
    spherical.paste(bottom_line_color, [0, int(pos_y + source_scaled.size[1] / 2),
                                        spherical.size[0], spherical.size[1]])
    spherical.paste(source_scaled, (out_half_width, pos_y))
    if mirror_x:
        source_scaled = ImageOps.mirror(source_scaled)
    spherical.paste(source_scaled, (out_half_width - source_scaled.size[0], pos_y))

    spherical.save(out_file_name)
