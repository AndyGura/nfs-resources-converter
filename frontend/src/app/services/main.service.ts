import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { EelDelegateService } from './eel-delegate.service';

@Injectable({
  providedIn: 'root'
})
export class MainService {

  resourceData$: BehaviorSubject<ReadData | null> = new BehaviorSubject<ReadData | null>(null);
  resourceError$: BehaviorSubject<ReadError | null> = new BehaviorSubject<ReadError | null>(null);

  readonly changedDataBlocks: { [key: string]: any } = {};

  constructor(readonly eelDelegate: EelDelegateService) {
    this.eelDelegate.openedResource$.subscribe((value) => {
      Object.keys(this.changedDataBlocks).forEach(key => {
        delete this.changedDataBlocks[key];
      });
      if (!value) {
        this.resourceData$.next(null);
        this.resourceError$.next(null);
      } else if ((value as any).block_class_mro) {
        this.resourceData$.next(value as ReadData);
        this.resourceError$.next(null);
      } else {
        this.resourceData$.next(null);
        this.resourceError$.next(value as ReadError);
      }
    });
  }

  get hasUnsavedChanges(): boolean {
    return Object.keys(this.changedDataBlocks).length > 0;
  }
}
