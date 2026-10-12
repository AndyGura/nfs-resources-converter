// An unloaded lazy part (archive entry, bundle chunk) rendered by the backend: a dict with the values known without
// parsing it (alias, chunk id) and this marker. `MainService.ensureLoaded` replaces its content in place with the
// parsed data
export const LAZY_MARKER = '__lazy__';

export const isLazyStub = (data: any): boolean =>
  !!data && typeof data === 'object' && !Array.isArray(data) && data[LAZY_MARKER] === true;
