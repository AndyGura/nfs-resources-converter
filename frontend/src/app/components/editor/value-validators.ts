// mirrors library/read_blocks/misc/value_validators.py
export type ValueValidator =
  | { type: 'eq'; expected_value: any }
  | { type: 'or'; possible_values: any[] }
  | { type: 'lt' | 'lte' | 'gt' | 'gte'; value: number }
  | { type: 'and'; validators: ValueValidator[] };

export type NumberRange = { min: number | null; max: number | null };

// range a numeric field's input allows: the integer width bounds of the schema (`min_value` / `max_value`), narrowed
// by the comparison validators. A strict bound (`lt` / `gt`) is one `value_interval` inside the value
export const numberRange = (schema: any): NumberRange => {
  const range: NumberRange = {
    min: typeof schema?.min_value === 'number' ? schema.min_value : null,
    max: typeof schema?.max_value === 'number' ? schema.max_value : null,
  };
  const step = typeof schema?.value_interval === 'number' ? schema.value_interval : 0;
  const narrow = (v: ValueValidator | undefined) => {
    if (!v) return;
    switch (v.type) {
      case 'lt':
      case 'lte': {
        const max = v.type === 'lt' ? v.value - step : v.value;
        range.max = range.max === null ? max : Math.min(range.max, max);
        break;
      }
      case 'gt':
      case 'gte': {
        const min = v.type === 'gt' ? v.value + step : v.value;
        range.min = range.min === null ? min : Math.max(range.min, min);
        break;
      }
      case 'and':
        v.validators.forEach(narrow);
        break;
    }
  };
  narrow(schema?.value_validator);
  return range;
};

export const clampToRange = (value: number, range: NumberRange): number => {
  if (range.max !== null && value > range.max) return range.max;
  if (range.min !== null && value < range.min) return range.min;
  return value;
};
