export const joinId = (a: string, b: string | number) => a + (a.includes('__') ? '/' : '__') + b;
