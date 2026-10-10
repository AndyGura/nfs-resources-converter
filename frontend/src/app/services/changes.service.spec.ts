import { NgZone } from '@angular/core';
import { BehaviorSubject, Subject } from 'rxjs';
import { ChangesService } from './changes.service';

describe('ChangesService', () => {
  let service: ChangesService;
  let resolveFeUpdate: (() => void)[];
  let revisions: [number, number];

  beforeEach(() => {
    resolveFeUpdate = [];
    revisions = [0, 0];
    const api: any = {
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
});
