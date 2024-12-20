export const blockClassStr = (schema: BlockSchema): string => {
  let finalClassName = schema.block_class_mro.split('__')[0];
  if (finalClassName === 'ArrayBlock') {
    return blockClassStr(schema.child_schema) + '[]';
  }
  return finalClassName;
};
