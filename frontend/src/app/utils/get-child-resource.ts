import { joinId } from './join-id';

const CHILD_RESOURCE_BUILDERS_MAP: { [key: string]: (resource: Resource, childName: string | number) => Resource } = {
  ArrayBlock: (resource, i) => ({
    id: joinId(resource.id, i),
    name: '' + i,
    data: resource.data[i],
    schema: resource.schema.child_schema,
  }),
  CompoundBlock: (resource, key) => ({
    id: joinId(resource.id, key),
    name: '' + key,
    data: resource.data[key],
    schema: resource.schema.fields.find((f: any) => f.name == key)!.schema,
  }),
  DelegateBlock: (resource, key) => {
    if (key != 'data') {
      throw new Error(`Trying to get child with key ${key} from DelegateBlock`);
    }
    return {
      id: joinId(resource.id, 'data'),
      name: '',
      data: resource.data.data,
      schema: resource.schema.possible_resource_schemas[resource.data.choice_index],
    };
  },
};

export const getChildResource = (resource: Resource, childName: string | number): Resource => {
  for (const className of resource.schema.block_class_mro.split('__')) {
    if (CHILD_RESOURCE_BUILDERS_MAP[className]) {
      return CHILD_RESOURCE_BUILDERS_MAP[className](resource, childName);
    }
  }
  throw new Error(`Cannot get child resource from block class ${resource.schema.block_class_mro}`);
};
