import { BehaviorSubject } from 'rxjs';
import { ChecksService } from './checks.service';

describe('ChecksService', () => {
  let service: ChecksService;
  let api: any;
  let resolveChecks: ((state: string) => void)[];

  beforeEach(() => {
    resolveChecks = [];
    api = {
      openedResourcePath$: new BehaviorSubject<string | null>(null),
      openedResource$: new BehaviorSubject<any>(null),
      getWarnings: jasmine
        .createSpy('getWarnings')
        .and.callFake(() => Promise.resolve([{ id: 'F.PBS__data', message: 'w' }])),
      getCompatibilityGames: jasmine.createSpy('getCompatibilityGames').and.callFake(() =>
        Promise.resolve([
          { alias: 'tnfs', title: 'TNFS' },
          { alias: 'nfs2', title: 'NFS2' },
        ]),
      ),
      checkCompatibility: jasmine
        .createSpy('checkCompatibility')
        .and.callFake(
          (game: string) => new Promise(resolve => resolveChecks.push(state => resolve({ game, state, problems: [] }))),
        ),
    };
    const changes: any = { settled: () => Promise.resolve() };
    service = new ChecksService(api, changes);
  });

  afterEach(() => service.ngOnDestroy());

  const flush = async () => {
    for (let i = 0; i < 10; i++) await Promise.resolve();
  };

  it('polls warnings of an opened file only', async () => {
    await flush();
    expect(api.getWarnings).not.toHaveBeenCalled();
    api.openedResourcePath$.next('F.PBS');
    api.openedResource$.next({ id: 'F.PBS', name: 'F.PBS', schema: {}, data: {} });
    await flush();
    expect(service.warnings$.value).toEqual([{ id: 'F.PBS__data', message: 'w' }]);

    api.openedResourcePath$.next(null);
    api.openedResource$.next(null);
    expect(service.warnings$.value).toEqual([]);
  });

  it('checks the games one by one', async () => {
    const done = service.checkCompatibility();
    await flush();
    expect(service.compatibility$.value.map(c => c.state)).toEqual(['loading', 'loading']);
    expect(api.checkCompatibility).toHaveBeenCalledTimes(1);

    resolveChecks[0]('compatible');
    await flush();
    expect(service.compatibility$.value.map(c => c.state)).toEqual(['compatible', 'loading']);
    expect(api.checkCompatibility).toHaveBeenCalledTimes(2);

    resolveChecks[1]('unknown');
    await done;
    expect(service.compatibility$.value.map(c => c.state)).toEqual(['compatible', 'unknown']);
  });

  it('drops the results of a run started over', async () => {
    const first = service.checkCompatibility();
    await flush();
    const second = service.checkCompatibility();
    await flush();
    resolveChecks[0]('not_compatible');
    await first;
    expect(service.compatibility$.value.map(c => c.state)).toEqual(['loading', 'loading']);
    resolveChecks[1]('compatible');
    await flush();
    resolveChecks[2]('compatible');
    await second;
    expect(service.compatibility$.value.map(c => c.state)).toEqual(['compatible', 'compatible']);
  });
});
