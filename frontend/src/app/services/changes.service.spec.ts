import { NgZone } from '@angular/core';
import { BehaviorSubject, Subject } from 'rxjs';
import { ChangesService } from './changes.service';

describe('ChangesService', () => {
  let service: ChangesService;
  let resolveFeUpdate: (() => void)[];
  let revisions: [number, number];
  let api: any;

  beforeEach(() => {
    resolveFeUpdate = [];
    revisions = [0, 0];
    api = {
      openedResource$: new BehaviorSubject<any>({ id: 'f', name: 'f', schema: {}, data: { b: { a: 1 } } }),
      onAppendChanges$: new Subject(),
      onFileOpened$: new Subject(),
      onFeUpdate: jasmine
        .createSpy('onFeUpdate')
        .and.callFake(() => new Promise<void>(resolve => resolveFeUpdate.push(resolve))),
      getRevisions: jasmine.createSpy('getRevisions').and.callFake(() => Promise.resolve(revisions)),
    };
    service = new ChangesService(api, { run: (fn: () => void) => fn() } as NgZone);
  });

  it('settles once the backend has every change', async () => {
    let settled = false;
    service.appendChanges({ timestamp: 0, op: 'set', id: 'f__b/a', oldValue: 1, newValue: 2 }).then();
    service.settled().then(() => (settled = true));
    await Promise.resolve();
    expect(settled).toBeFalse();

    revisions = [0, 1];
    resolveFeUpdate.forEach(r => r());
    await service.settled();
    expect(settled).toBeTrue();
    expect(service.hasUnsavedChanges$.value).toBeTrue();
  });

  it('settles at once without pending calls', async () => {
    await service.settled();
    expect(service.hasUnsavedChanges$.value).toBeFalse();
  });

  it('applies backend changes, skipping the parts this window has not loaded', () => {
    const data = {
      children: [
        { alias: 'pal', __lazy__: true },
        { alias: 'horz', item: { data: { width: 1 } } },
      ],
    };
    api.openedResource$.next({ id: 'f', name: 'f', schema: {}, data });
    api.onAppendChanges$.next([
      [
        {
          id: '',
          timestamp: 0,
          op: 'bundle',
          changes: [
            { id: 'f__children/0/item/data/width', timestamp: 0, op: 'set', oldValue: 1, newValue: 2 },
            { id: 'f__children/0/item', timestamp: 0, op: 'set', oldValue: {}, newValue: { data: {} } },
            { id: 'f__children/0/alias', timestamp: 0, op: 'set', oldValue: 'pal', newValue: '!PAL' },
            { id: 'f__children/1/item/data/width', timestamp: 0, op: 'set', oldValue: 1, newValue: 3 },
            { id: 'f__children', timestamp: 0, op: 'array_insert', index: 2, value: { alias: 'sun' } },
          ],
        },
      ],
    ]);
    expect(data.children[0]).toEqual({ alias: '!PAL', __lazy__: true });
    expect(data.children[1].item!.data.width).toBe(3);
    expect(data.children.map(c => c.alias)).toEqual(['!PAL', 'horz', 'sun']);
  });
});
