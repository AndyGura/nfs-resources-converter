export function deepEqual(obj1: any, obj2: any): boolean {
  // Check for primitive equality (and handle null/undefined)
  if (obj1 === obj2) return true;

  // If either is not an object or is null, they are not equal
  if (typeof obj1 !== 'object' || obj1 === null || typeof obj2 !== 'object' || obj2 === null) {
    return false;
  }

  // Get keys of both objects
  const keys1 = Object.keys(obj1);
  const keys2 = Object.keys(obj2);

  // If number of keys is different, they are not equal
  if (keys1.length !== keys2.length) return false;

  // Recursively compare each key and value
  for (const key of keys1) {
    if (!keys2.includes(key) || !deepEqual(obj1[key], obj2[key])) {
      return false;
    }
  }

  return true;
}
