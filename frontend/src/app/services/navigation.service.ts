import { Injectable } from '@angular/core';
import { BehaviorSubject, combineLatest } from 'rxjs';
import { MainService } from './main.service';
import { getChildResource } from '../utils/get-child-resource';

@Injectable({
  providedIn: 'root',
})
export class NavigationService {
  public readonly navigationPath$: BehaviorSubject<string[]> = new BehaviorSubject<string[]>([]);
  public readonly resourceToRender$: BehaviorSubject<Resource | null> = new BehaviorSubject<Resource | null>(null);

  public navigateToId(blockId: string): void {
    this.navigationPath$.next(blockId.substring(blockId.indexOf('__') + 2).split('/'));
  }

  public navigateBack(n: number): void {
    this.navigationPath$.next(this.navigationPath$.value.slice(0, this.navigationPath$.value.length - n));
  }

  constructor(private readonly main: MainService) {
    this.main.resource$.subscribe(r => {
      this.navigationPath$.next([]);
    });
    combineLatest([this.main.resource$, this.navigationPath$]).subscribe(([res, path]) => {
      let r = res;
      for (const p of path) {
        if (r) {
          r = getChildResource(r, p);
        }
      }
      this.resourceToRender$.next(r);
    });
  }
}
