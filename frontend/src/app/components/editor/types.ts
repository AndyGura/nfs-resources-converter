type Resource = {
  id: string;
  name: string;
  schema: BlockSchema;
  data: BlockData;
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
  required_value: any | null;
} & any;
type BlockData = any;
type ReadError = {
  error_class: string;
  error_text: string;
};

// type ReadData = {
//   block_class_mro: string;
//   block: {
//     custom_actions: CustomAction[];
//     is_serializable_to_disk: boolean;
//     unknown_fields?: string[];
//   } & any;
//   block_id: string;
//   editor_validators: any;
//   value: any;
// };

type CustomAction = {
  method: string;
  title: string;
  description: string;
  args: { id: string; title: string; type: string }[];
};
