import { clampToRange, numberRange } from './value-validators';

describe('numberRange', () => {
  const uint32 = { min_value: 0, max_value: 4294967295, value_interval: 1 };

  it('keeps the width bounds without a validator', () => {
    expect(numberRange(uint32)).toEqual({ min: 0, max: 4294967295 });
    expect(numberRange({ ...uint32, value_validator: { type: 'eq', expected_value: 3 } })).toEqual({
      min: 0,
      max: 4294967295,
    });
  });

  it('narrows the bounds with comparisons', () => {
    expect(numberRange({ ...uint32, value_validator: { type: 'lte', value: 60 } })).toEqual({ min: 0, max: 60 });
    expect(numberRange({ ...uint32, value_validator: { type: 'lt', value: 60 } })).toEqual({ min: 0, max: 59 });
    expect(numberRange({ ...uint32, value_validator: { type: 'gt', value: 5 } })).toEqual({ min: 6, max: 4294967295 });
    expect(
      numberRange({
        ...uint32,
        value_validator: {
          type: 'and',
          validators: [
            { type: 'gte', value: 10 },
            { type: 'lte', value: 60 },
          ],
        },
      }),
    ).toEqual({ min: 10, max: 60 });
  });

  it('never widens the width bounds', () => {
    expect(numberRange({ ...uint32, value_validator: { type: 'gte', value: -5 } })).toEqual({
      min: 0,
      max: 4294967295,
    });
  });
});

describe('clampToRange', () => {
  it('clamps to the bounds that are set', () => {
    expect(clampToRange(70, { min: 0, max: 60 })).toBe(60);
    expect(clampToRange(-1, { min: 0, max: 60 })).toBe(0);
    expect(clampToRange(30, { min: 0, max: 60 })).toBe(30);
    expect(clampToRange(1e9, { min: null, max: null })).toBe(1e9);
  });
});
