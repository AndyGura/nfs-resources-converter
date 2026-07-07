import { BlockSchema } from '../components/editor/types';

export const blockClassStr = (schema: BlockSchema): string => {
  if (!schema) return '';
  let finalClassName = schema.block_class_mro.split('__')[0];
  if (finalClassName === 'ArrayBlock') {
    return blockClassStr(schema.child_schema) + '[]';
  }
  return finalClassName;
};
