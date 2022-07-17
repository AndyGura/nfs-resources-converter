import os
from io import BufferedReader, BytesIO, SEEK_CUR


# this looks like a mess, but it is intended to be like that: by using local imports we dramatically increase
# performance, because we spawn process per file, and it doesn't need to load all those classes every time
def _find_block_class(file_name: str, header_str: str, header_bytes: bytes):
    if file_name:
        if file_name.endswith('.BNK'):
            from resources.eac.archives import SoundBank
            return SoundBank
        if file_name.endswith('.PBS_UNCOMPRESSED'):
            from resources.eac.car_specs import CarPerformanceSpec
            return CarPerformanceSpec
        elif file_name.endswith('.PDN_UNCOMPRESSED'):
            from resources.eac.car_specs import CarSimplifiedPerformanceSpec
            return CarSimplifiedPerformanceSpec
    if header_str:
        if file_name and header_str == '#ver' and file_name.endswith('INFO'):
            from resources.eac.misc import DashDeclarationFile
            return DashDeclarationFile
        elif header_str == '1SNh':
            from resources.eac.audios import AsfAudio
            return AsfAudio
        elif header_str in ['kVGT', 'SCHl']:
            from resources.eac.videos import FfmpegSupportedVideo
            return FfmpegSupportedVideo
        elif header_str == 'SHPI':
            from resources.eac.archives import ShpiArchive
            return ShpiArchive
        elif header_str == 'wwww':
            from resources.eac.archives import WwwwArchive
            return WwwwArchive
        elif header_str == 'FNTF':
            from resources.eac.fonts import FfnFont
            return FfnFont
        elif header_str == 'ORIP':
            from resources.eac.geometries import OripGeometry
            return OripGeometry
        elif header_str == 'EACS':
            from resources.eac.audios import EacsAudio
            return EacsAudio
    try:
        resource_id = header_bytes[0]
        if resource_id == 0x22:
            from resources.eac.palettes import Palette24BitDos
            return Palette24BitDos
        elif resource_id == 0x24:
            from resources.eac.palettes import Palette24Bit
            return Palette24Bit
        # TODO 41 (0x29) 16 bit dos palette
        elif resource_id == 0x2A:
            from resources.eac.palettes import Palette32Bit
            return Palette32Bit
        elif resource_id == 0x2D:
            from resources.eac.palettes import Palette16Bit
            return Palette16Bit
        elif resource_id == 0x78:
            from resources.eac.bitmaps import Bitmap16Bit0565
            return Bitmap16Bit0565
        elif resource_id == 0x7A:
            from resources.eac.bitmaps import Bitmap4Bit
            return Bitmap4Bit
        elif resource_id == 0x7B:
            from resources.eac.bitmaps import Bitmap8Bit
            return Bitmap8Bit
        elif resource_id == 0x7C:
            from resources.eac.palettes import PaletteReference
            return PaletteReference
        elif resource_id == 0x7D:
            from resources.eac.bitmaps import Bitmap32Bit
            return Bitmap32Bit
        elif resource_id == 0x7E:
            from resources.eac.bitmaps import Bitmap16Bit1555
            return Bitmap16Bit1555
        elif resource_id == 0x7F:
            from resources.eac.bitmaps import Bitmap24Bit
            return Bitmap24Bit
        # QFS1
        # if resource_id & 0b0001_0000:
        elif header_bytes[1] == 0xfb and (resource_id & 0b1111_1110) == 0x10:
            from resources.eac.archives import RefPackBlock
            return RefPackBlock
        # AL2.QFS
        elif header_bytes[1] == 0xfb and resource_id == 0b0100_0110:
            from resources.eac.archives import Qfs2Block
            return Qfs2Block
        # AL1.QFS
        elif header_bytes[1] == 0xfb and resource_id in [0b0011_0000, 0b0011_0010, 0b0011_0100, 0b0011_0001,
                                                         0b0011_0011,
                                                         0b0011_0101]:
            from resources.eac.archives import Qfs3Block
            return Qfs3Block
        elif resource_id == 0x11:
            from resources.eac.maps import TriMap
            return TriMap
    except IndexError:
        pass
    return None


def probe_block_class(binary_file: [BufferedReader, BytesIO], file_name: str = None, resources_to_pick=None):
    header_bytes = binary_file.read(4)
    binary_file.seek(-len(header_bytes), SEEK_CUR)
    try:
        header_str = header_bytes.decode('utf8')
    except UnicodeDecodeError:
        header_str = None
    block_class = _find_block_class(file_name, header_str, header_bytes)
    if block_class and (not resources_to_pick or block_class in resources_to_pick):
        return block_class
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
