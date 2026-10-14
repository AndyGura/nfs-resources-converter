import { Injectable, OnDestroy } from '@angular/core';
import { BehaviorSubject, combineLatest, Subscription } from 'rxjs';
import { ApiDelegateService } from './api/api-delegate.service';
import { BlockWarning, CompatibilityGame, CompatibilityReport, CompatibilityState } from './api/api-types';
import { ChangesService } from './changes.service';

export type GameCompatibility = {
  game: CompatibilityGame;
  state: CompatibilityState | 'loading' | 'error';
  report?: CompatibilityReport;
  error?: string;
};

// Warnings of the opened file (polled) and its game compatibility (on demand), see library/block_checks.py
@Injectable({
  providedIn: 'root',
})
export class ChecksService implements OnDestroy {
  static readonly WARNINGS_POLL_INTERVAL_MS = 1500;

  public readonly warnings$: BehaviorSubject<BlockWarning[]> = new BehaviorSubject<BlockWarning[]>([]);
  public readonly compatibility$: BehaviorSubject<GameCompatibility[]> = new BehaviorSubject<GameCompatibility[]>([]);
  // false until the games of the current check are known
  public readonly compatibilityGamesLoaded$: BehaviorSubject<boolean> = new BehaviorSubject<boolean>(false);

  private pollTimer: any = null;
  private pollInFlight = false;
  private fileGeneration = 0;
  private compatibilityRun = 0;
  private lastPath: string | null = null;
  private readonly subscription: Subscription;

  constructor(
    private readonly api: ApiDelegateService,
    private readonly changes: ChangesService,
  ) {
    this.subscription = combineLatest([this.api.openedResourcePath$, this.api.openedResource$]).subscribe(
      ([path, resource]) => {
        this.fileGeneration++;
        this.compatibilityRun++;
        this.compatibility$.next([]);
        this.compatibilityGamesLoaded$.next(false);
        if (path !== this.lastPath || !resource) {
          // a save or reload of the same file keeps the shown warnings until the next poll
          this.warnings$.next([]);
        }
        this.lastPath = path;
        if (path && resource && !resource.data?.error_class) {
          this.startPolling();
        } else {
          this.stopPolling();
        }
      },
    );
  }

  ngOnDestroy() {
    this.stopPolling();
    this.subscription.unsubscribe();
  }

  private startPolling() {
    this.stopPolling();
    this.pollWarnings().then();
    this.pollTimer = setInterval(() => this.pollWarnings(), ChecksService.WARNINGS_POLL_INTERVAL_MS);
  }

  private stopPolling() {
    if (this.pollTimer !== null) {
      clearInterval(this.pollTimer);
      this.pollTimer = null;
    }
  }

  public async pollWarnings(): Promise<void> {
    if (this.pollInFlight) return;
    this.pollInFlight = true;
    const generation = this.fileGeneration;
    try {
      const warnings = (await this.api.getWarnings()) || [];
      if (generation !== this.fileGeneration) return;
      if (JSON.stringify(warnings) !== JSON.stringify(this.warnings$.value)) {
        this.warnings$.next(warnings);
      }
    } catch (err) {
      console.warn('Cannot get warnings', err);
    } finally {
      this.pollInFlight = false;
    }
  }

  // checks every game, one request per game, so the results come in one by one
  public async checkCompatibility(): Promise<void> {
    const run = ++this.compatibilityRun;
    this.compatibilityGamesLoaded$.next(false);
    // the check sees every edit made so far
    await this.changes.settled();
    // only the games the opened file is made for
    const games = await this.api.getCompatibilityGames();
    if (run !== this.compatibilityRun) return;
    const results: GameCompatibility[] = games.map(game => ({ game, state: 'loading' }));
    this.compatibility$.next(results);
    this.compatibilityGamesLoaded$.next(true);
    for (let i = 0; i < results.length; i++) {
      let result: GameCompatibility;
      try {
        const report = await this.api.checkCompatibility(results[i].game.alias);
        result = { game: results[i].game, state: report.state, report };
      } catch (err: any) {
        result = { game: results[i].game, state: 'error', error: err?.message || err?.errorText || `${err}` };
      }
      if (run !== this.compatibilityRun) return;
      results[i] = result;
      this.compatibility$.next([...results]);
    }
  }
}
