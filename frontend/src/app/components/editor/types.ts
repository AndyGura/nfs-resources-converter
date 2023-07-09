// TODO improve typing here
type ReadData = {
  block_class_mro: string;
  block: {
    custom_actions: CustomAction[];
    is_serializable_to_disk: boolean;
    unknown_fields?: string[];
  } & any;
  block_id: string;
  editor_validators: any;
  value: any;
};

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
