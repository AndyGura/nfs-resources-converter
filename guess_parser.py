from io import BufferedReader, SEEK_CUR

from parsers.resources.archives import (
    SHPIArchive,
    WwwwArchive,
    SoundBank,
)
from parsers.resources.audios import ASFAudio, EacsAudio
from parsers.resources.base import BaseResource
from parsers.resources.bitmaps import (
    Bitmap8Bit,
    Bitmap16Bit1555,
    Bitmap16Bit0565,
    Bitmap24Bit,
    Bitmap32Bit)
from parsers.resources.compressed import (
    RefPackArchive,
    Qfs2Archive,
    Qfs3Archive,
)
from parsers.resources.geometries import OripGeometryResource
from parsers.resources.maps import TriMapResource
from parsers.resources.misc import TextResource, BinaryResource
from parsers.resources.palettes import (
    Palette24BitDos,
    Palette24Bit,
    Palette32Bit,
    Palette16Bit,
)
from parsers.resources.videos import FFmpegSupportedVideo


def get_resource_class(binary_file: BufferedReader, file_name: str = None) -> BaseResource:
    if file_name:
        if file_name.endswith('.BNK'):
            return SoundBank()
        elif file_name.endswith('.PBS_UNCOMPRESSED') or file_name.endswith('.PDN_UNCOMPRESSED'):
            return BinaryResource()
    header_bytes = binary_file.read(4)
    binary_file.seek(-len(header_bytes), SEEK_CUR)
    try:
        header_str = header_bytes.decode('utf8')
        if header_str == 'SHPI':
            return SHPIArchive()
        elif header_str == 'FNTF':
            print('FFN file (NFS1 font)')
            raise NotImplementedError('Don`t have parser for such resource')
        elif header_str == 'ORIP':
            return OripGeometryResource()
        elif header_str == 'wwww':
            return WwwwArchive()
        elif header_str in ['kVGT', 'SCHl']:
            return FFmpegSupportedVideo()
        elif header_str == '1SNh':
            return ASFAudio()
        elif header_str == 'EACS':
            return EacsAudio()
    except UnicodeDecodeError:
        pass
    try:
        resource_id = header_bytes[0]
    except IndexError:
        raise NotImplementedError('Don`t have parser for such resource. header_bytes are missed')
    # QFS1
    # if resource_id & 0b0001_0000:
    if header_bytes[1] == 0xfb and (resource_id & 0b1111_1110) == 0x10:
        return RefPackArchive()
    # AL2.QFS
    elif header_bytes[1] == 0xfb and resource_id == 0b0100_0110:
        return Qfs2Archive()
    # AL1.QFS
    elif header_bytes[1] == 0xfb and resource_id in [0b0011_0000, 0b0011_0010, 0b0011_0100, 0b0011_0001, 0b0011_0011, 0b0011_0101]:
        return Qfs3Archive()
    elif resource_id == 0x0A:
        # unknown resource with length == 84
        # looks like some info about sprite positioning on screen
        return BinaryResource(id=resource_id, length=84, save_binary_file=False)
    elif resource_id == 0x11 and header_bytes[1] == 0x00 and header_bytes[2] == 0x00 and header_bytes[3] == 0x00:
        return TriMapResource()
    elif resource_id == 0x22:
        return Palette24BitDos()
    elif resource_id == 0x24:
        return Palette24Bit()
    # 41 (0x29) 16 bit dos palette
    elif resource_id == 0x2A:
        return Palette32Bit()
    elif resource_id == 0x2D:
        return Palette16Bit()
    elif resource_id == 0x6F:
        return TextResource()
    elif resource_id == 0x78:
        return Bitmap16Bit0565()
    elif resource_id == 0x7B:
        return Bitmap8Bit()
    elif resource_id == 0x7C:
        # it looks like we often see 0x7C after texture, No idea what's this, doesnt look like alpha channel container
        return BinaryResource(id=resource_id, save_binary_file=False)
    elif resource_id == 0x7D:
        return Bitmap32Bit()
    elif resource_id == 0x7E:
        return Bitmap16Bit1555()
    elif resource_id == 0x7F:
        return Bitmap24Bit()
    else:
        raise NotImplementedError('Don`t have parser for such resource')
