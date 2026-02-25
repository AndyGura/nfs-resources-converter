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
  serializable_to_disc: boolean;
  value_validator?: { type: 'eq', expected_value: any } | { type: 'or', possible_values: any[] };
  custom_actions?: CustomAction[]
} & any;
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
  | { type: 'file_output', file_name_suffix: string }
  | { type: 'number' }
  | { type: 'string' }
  );
