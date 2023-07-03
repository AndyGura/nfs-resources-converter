from typing import Dict

from library.helpers.data_wrapper import DataWrapper
from library.read_data import ReadData
from serializers.base import ResourceSerializer


class DataTransferSerializer(ResourceSerializer):

    @staticmethod
    def _serialize_block(block):
        from library.read_blocks.data_block import DataBlock
        result = {k: v if not isinstance(v, DataBlock) else DataTransferSerializer._serialize_block(v)
                  for (k, v) in block.__dict__.items()
                  if k not in ['instance_fields', 'instance_fields_map']}
        from library.read_blocks.compound import CompoundBlock
        if isinstance(block, CompoundBlock):
            result['unknown_fields'] = block.Fields.unknown_fields
        return {
            'custom_actions': block.list_custom_actions(),
            **result,
        }

    def serialize(self, data: ReadData, skip_block_info=False) -> Dict:
        if not isinstance(data, ReadData):
            if isinstance(data, Exception):
                return {
                    'error_class': data.__class__.__name__,
                    'error_text': str(data),
                }
            try:
                return data.__dict__
            except AttributeError:
                return data
        if isinstance(data.value, DataWrapper):
            value = {k: self.serialize(v) for k, v in data.value.items()}
        elif isinstance(data.value, list):
            array_scoped_block = None
            try:
                array_scoped_block = data.block.child
            except Exception:
                pass
            value = [self.serialize(x, isinstance(x, ReadData) and x.block == array_scoped_block) for x in data.value]
        elif isinstance(data.value, bytes):
            value = list(data.value)
        else:
            value = data.value
        if skip_block_info:
            return {
                'block_class_mro': '__'.join(
                    [x.__name__ for x in data.block.__class__.mro() if x.__name__ not in ['object', 'ABC']]),
                'block_id': data.block_state['id'],
                'editor_validators': data.block.get_editor_validators(data.block_state),
                'value': value
            }
        return {
            'block_class_mro': '__'.join(
                [x.__name__ for x in data.block.__class__.mro() if x.__name__ not in ['object', 'ABC']]),
            'block': DataTransferSerializer._serialize_block(block=data.block),
            'block_id': data.block_state['id'],
            'editor_validators': data.block.get_editor_validators(data.block_state),
            'value': value
        }
