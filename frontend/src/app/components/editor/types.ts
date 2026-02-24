type Resource<BD = BlockData> = {
  id: string;
  name: string;
  schema: BlockSchema;
  data: BD;
};

type ResourceError = {
  id: string;
  name: string;
  schema: null;
  data: ReadError;
};

// TODO improve typing here
type BlockSchema = {
  block_class_mro: string;
  serializable_to_disc: boolean;
  value_validator?: { type: 'eq', expected_value: any } | { type: 'or', possible_values: any[] };
} & any;
type BlockData = any;
type ReadError = {
  error_class: string;
  error_text: string;
};

type CustomAction = {
  method: string;
  title: string;
  description: string;
  args: { id: string; title: string; type: string }[];
};
