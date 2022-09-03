import settings
from library.read_blocks.delegate import DelegateBlock
from library.read_blocks.data_block import DataBlock
from library.utils import my_import
from .base import BaseFileSerializer
from .palettes import PaletteSerializer
from .bitmaps import BitmapSerializer, BitmapWithPaletteSerializer
from .fonts import FfnFontSerializer
from .json import JsonSerializer
from .maps import TriMapSerializer
from .geometries import OripGeometrySerializer
from .archives import ShpiArchiveSerializer, WwwwArchiveSerializer, SoundBankSerializer
from .videos import FfmpegSupportedVideoSerializer
from .audios import EacsAudioSerializer, FfmpegSupportedAudioSerializer
from .data_transfer import DataTransferSerializer


def get_serializer(block: DataBlock) -> BaseFileSerializer:
    if isinstance(block, Exception):
        raise block
    if isinstance(block, DelegateBlock):
        block = block.delegated_block
    serializer_class_name = settings.SERIALIZER_CLASSES.get(block.__class__.__name__)
    serializer_class = None
    if serializer_class_name:
        try:
            serializer_class = my_import(f'serializers.{serializer_class_name}')
        except ImportError as ex:
            pass
    if not serializer_class_name or not serializer_class:
        raise NotImplementedError(f'Serializer for resource {block.__class__.__name__} not implemented!')
    return serializer_class()
