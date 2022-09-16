import inspect
import sys
from typing import Dict

from library.read_data import ReadData
from library.helpers.data_wrapper import DataWrapper
from serializers.base import ResourceSerializer


class DataTransferSerializer(ResourceSerializer):

    @staticmethod
    def _serialize_block(block):
        from library.read_blocks.data_block import DataBlock
        return {k: v if not isinstance(v, DataBlock) else DataTransferSerializer._serialize_block(v)
                for (k, v) in block.__dict__.items()}

    @staticmethod
    def _is_serialized_read_data(data: Dict):
        return (isinstance(data, dict)
                and 'block_class_module' in data
                and 'block_class_mro' in data
                and 'block' in data
                and 'block_state' in data
                and 'value' in data)

    @staticmethod
    def _deserialize_block_value(value):
        if isinstance(value, dict):
            return DataWrapper({k: DataTransferSerializer._deserialize_block_value(
                v) if not DataTransferSerializer._is_serialized_read_data(
                v) else DataTransferSerializer._deserialize_read_data(v)
                                for k, v in value.items()})
        elif isinstance(value, list):
            return [DataTransferSerializer._deserialize_block_value(
                x) if not DataTransferSerializer._is_serialized_read_data(
                x) else DataTransferSerializer._deserialize_read_data(x)
                    for x in value]
        return value

    @staticmethod
    def _deserialize_read_data(data: Dict) -> ReadData:
        cls = getattr(sys.modules[data['block_class_module']], data['block_class_mro'].split('__')[0])
        block = cls(**data['block'])
        value = DataTransferSerializer._deserialize_block_value(data['value'])
        return ReadData(value=value,
                        block=block,
                        block_state=data['block_state'])

    def serialize(self, data: ReadData) -> Dict:
        if not isinstance(data, ReadData):
            try:
                return data.__dict__
            except AttributeError:
                return data
        if isinstance(data.value, DataWrapper):
            value = { k: self.serialize(v) for k, v in data.value.items() }
        elif isinstance(data.value, list):
            value = [self.serialize(x) for x in data.value]
        elif isinstance(data.value, bytes):
            value = list(data.value)
        else:
            value = data.value
        return {
            'block_class_module': inspect.getmodule(data.block.__class__).__name__,
            'block_class_mro': '__'.join(
                [x.__name__ for x in data.block.__class__.mro() if x.__name__ not in ['object', 'ABC']]),
            'block': DataTransferSerializer._serialize_block(block=data.block),
            'block_state': data.block_state,
            'editor_validators': data.block.get_editor_validators(data.block_state),
            'value': value
        }

    def deserialize(self, data: Dict) -> ReadData:
        return DataTransferSerializer._deserialize_read_data(data)
