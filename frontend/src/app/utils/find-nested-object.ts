const isObject = (value: any) => {
  return !!(value && typeof value === 'object');
};

export const findNestedObjects: (
  obj: any,
  key: string,
  value: any,
  path?: Array<string | number>,
) => [any, Array<string | number>][] = (object = {}, keyToMatch, valueToMatch, path = []) => {
  const results: [any, Array<string | number>][] = [];
  if (isObject(object)) {
    const entries = Object.entries(object);
    for (let i = 0; i < entries.length; i += 1) {
      const [objectKey, objectValue] = entries[i];
      if (objectKey === keyToMatch && objectValue === valueToMatch) {
        results.push([object, path]);
      } else if (isObject(objectValue)) {
        const childRes = findNestedObjects(objectValue, keyToMatch, valueToMatch, [...path, objectKey]);
        results.push(...childRes);
      }
    }
  }
  return results;
};
