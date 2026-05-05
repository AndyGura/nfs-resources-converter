export const joinId = (a: string, ...b: (string | number)[]) => a + (a.includes('__') ? '/' : '__') + b.join('/');

export const idSuffix = (baseId: string, id: string) => {
  if (baseId === id) {
    return '';
  }
  let next = id.substring(baseId.length);
  if (next.startsWith('/')) {
    return next.substring(1);
  } else if (next.startsWith('__')) {
    return next.substring(2);
  } else {
    throw new Error('Cannot extract valid suffix from id "' + id + '" in "' + baseId + '"');
  }
}

export const lastIdPart = (id: string) => {
  const parts = id.split(/\/|__/).filter(part => part !== '');
  return parts[parts.length - 1];
};
