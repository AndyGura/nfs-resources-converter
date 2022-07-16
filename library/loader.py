import os
from io import BufferedReader, SEEK_CUR, BytesIO

from library.read_blocks.exceptions import BlockIntegrityException
from resources.eac.archives import ShpiArchive, WwwwArchive, RefPackBlock, Qfs2Block, Qfs3Block, SoundBank
from resources.eac.audios import EacsAudio, AsfAudio
from resources.eac.bitmaps import (
    Bitmap32Bit,
    Bitmap16Bit1555,
    Bitmap16Bit0565,
    Bitmap24Bit,
    Bitmap8Bit,
    Bitmap4Bit,
)
from resources.eac.car_specs import (
    CarPerformanceSpec,
    CarSimplifiedPerformanceSpec,
)
from resources.eac.fonts import (
    FfnFont,
)
from resources.eac.geometries import OripGeometry
from resources.eac.maps import TriMap
from resources.eac.misc import DashDeclarationFile
from resources.eac.palettes import (
    PaletteReference,
    Palette16BitResource,
    Palette32BitResource,
    Palette24BitResource,
    Palette24BitDosResource,
)
from resources.eac.videos import FfmpegSupportedVideo


def probe_block_class(binary_file: [BufferedReader, BytesIO], file_name: str = None, resources_to_pick=None):
    if file_name:
        if file_name.endswith('.BNK'):
            return SoundBank
        if file_name.endswith('.PBS_UNCOMPRESSED') and (
                not resources_to_pick or CarPerformanceSpec in resources_to_pick):
            return CarPerformanceSpec
        elif file_name.endswith('.PDN_UNCOMPRESSED'):
            return CarSimplifiedPerformanceSpec
    header_bytes = binary_file.read(4)
    binary_file.seek(-len(header_bytes), SEEK_CUR)
    try:
        header_str = header_bytes.decode('utf8')
        if file_name and header_str == '#ver' and file_name.endswith('INFO') and (
                not resources_to_pick or DashDeclarationFile in resources_to_pick):
            return DashDeclarationFile
        elif header_str == '1SNh' and (not resources_to_pick or AsfAudio in resources_to_pick):
            return AsfAudio
        elif header_str in ['kVGT', 'SCHl'] and (not resources_to_pick or FfmpegSupportedVideo in resources_to_pick):
            return FfmpegSupportedVideo
        elif header_str == 'SHPI' and (not resources_to_pick or ShpiArchive in resources_to_pick):
            return ShpiArchive
        elif header_str == 'wwww' and (not resources_to_pick or WwwwArchive in resources_to_pick):
            return WwwwArchive
        elif header_str == 'FNTF' and (not resources_to_pick or FfnFont in resources_to_pick):
            return FfnFont
        elif header_str == 'ORIP' and (not resources_to_pick or OripGeometry in resources_to_pick):
            return OripGeometry
        elif header_str == 'EACS' and (not resources_to_pick or EacsAudio in resources_to_pick):
            return EacsAudio
    except UnicodeDecodeError:
        pass
    try:
        resource_id = header_bytes[0]
        if resource_id == 0x22 and (not resources_to_pick or Palette24BitDosResource in resources_to_pick):
            return Palette24BitDosResource
        elif resource_id == 0x24 and (not resources_to_pick or Palette24BitResource in resources_to_pick):
            return Palette24BitResource
        # TODO 41 (0x29) 16 bit dos palette
        elif resource_id == 0x2A and (not resources_to_pick or Palette32BitResource in resources_to_pick):
            return Palette32BitResource
        elif resource_id == 0x2D and (not resources_to_pick or Palette16BitResource in resources_to_pick):
            return Palette16BitResource
        elif resource_id == 0x78 and (not resources_to_pick or Bitmap16Bit0565 in resources_to_pick):
            return Bitmap16Bit0565
        elif resource_id == 0x7A and (not resources_to_pick or Bitmap4Bit in resources_to_pick):
            return Bitmap4Bit
        elif resource_id == 0x7B and (not resources_to_pick or Bitmap8Bit in resources_to_pick):
            return Bitmap8Bit
        elif resource_id == 0x7C and (not resources_to_pick or PaletteReference in resources_to_pick):
            return PaletteReference
        elif resource_id == 0x7D and (not resources_to_pick or Bitmap32Bit in resources_to_pick):
            return Bitmap32Bit
        elif resource_id == 0x7E and (not resources_to_pick or Bitmap16Bit1555 in resources_to_pick):
            return Bitmap16Bit1555
        elif resource_id == 0x7F and (not resources_to_pick or Bitmap24Bit in resources_to_pick):
            return Bitmap24Bit
        # QFS1
        # if resource_id & 0b0001_0000:
        elif header_bytes[1] == 0xfb and (resource_id & 0b1111_1110) == 0x10:
            return RefPackBlock
        # AL2.QFS
        elif header_bytes[1] == 0xfb and resource_id == 0b0100_0110:
            return Qfs2Block
        # AL1.QFS
        elif header_bytes[1] == 0xfb and resource_id in [0b0011_0000, 0b0011_0010, 0b0011_0100, 0b0011_0001,
                                                         0b0011_0011,
                                                         0b0011_0101]:
            return Qfs3Block
        elif resource_id == 0x11 and header_bytes[1] == 0x00 and header_bytes[2] == 0x00 and header_bytes[3] == 0x00:
            return TriMap
    except IndexError:
        raise BlockIntegrityException('Don`t have parser for such resource. header_bytes are missed')
    raise NotImplementedError('Don`t have parser for such resource')


# id example: /media/data/nfs/SIMDATA/CARFAMS/LDIABL.CFM__1/frnt
def require_resource(id: str):
    file_path = id.split('__')[0]
    resource = require_file(file_path)
    if file_path == id:
        return resource
    resource_path = [x for x in id.split('__')[1].split('/') if x]
    for key in resource_path:
        if isinstance(resource, list) and key.isdigit():
            try:
                resource = resource[int(key)]
                continue
            except KeyError:
                return None
        try:
            resource = getattr(resource, key)
        except AttributeError:
            return None
        if not resource:
            return None
    return resource


# not shared between processes: in most cases if file requires another resource, it is in the same file, or it
# requires one external file multiple times. It will be more time-consuming to serialize/deserialize it for sharing
# between processes than load some file multiple times. + we avoid potential memory leaks
files_cache = {}


def require_file(path: str):
    block = files_cache.get(path)
    if block is None:
        with open(path, 'rb', buffering=100 * 1024 * 1024) as bdata:
            block_class = probe_block_class(bdata, path)
            block = block_class()
            files_cache[path] = block
            block.id = path
            block.read(bdata, os.path.getsize(path))
    return block
