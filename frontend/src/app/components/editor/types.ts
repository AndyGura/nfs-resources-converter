import { deepEqual } from '../../utils/deep-equals';

export type Resource<BD = BlockData> = {
  id: string;
  name: string;
  schema: BlockSchema;
  data: BD;
};

export type ResourceError = {
  id: string;
  name: string;
  schema: null;
  data: ReadError;
};

// TODO improve typing here
export type BlockSchema = {
  block_class_mro: string;
  serialization?: {
    file_type: string | null;
    is_directory: boolean | null;
    output_file_name_suffix: string | null;
    reversible: boolean;
    reversible_settings_patch: any;
  } | null;
  hide_navigation_bar?: boolean;
  value_validator?: { type: 'eq'; expected_value: any } | { type: 'or'; possible_values: any[] };
  custom_actions?: CustomAction[];
} & any;

export const schemaEquals = (schemaA: BlockSchema, schemaB: BlockSchema): boolean => {
  if (schemaA === schemaB) return true;
  if (!schemaA || !schemaB) return !schemaA && !schemaB;
  if (schemaA.block_class_mro !== schemaB.block_class_mro) return false;

  return deepEqual(schemaA, schemaB);
};

export type BlockData = any;
export type ReadError = {
  error_class: string;
  error_text: string;
};

export type CustomAction = {
  method: string;
  title: string;
  description: string;
  is_pure: boolean;
  args: CustomActionArgument[];
};

export type CustomActionArgument = { id: string; title: string } & (
  | { type: 'file_output'; file_name_suffix: string }
  | { type: 'number'; default?: number }
  | { type: 'string'; default?: string }
  | { type: 'bool'; default?: boolean }
  | { type: 'enum_string'; choices: string[]; default?: string }
);
