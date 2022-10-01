// TODO improve typing here
type ReadData = {
  block_class_mro: string,
  block: any,
  block_state: any,
  editor_validators: any,
  value: any,
};

type ReadError = {
  error_class: string,
  error_text: string,
}

type CustomAction = {
  method: string,
  title: string,
  description: string,
  args: { id: string, title: string, type: string }[]
};
