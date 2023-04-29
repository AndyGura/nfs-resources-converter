import { Injectable } from '@angular/core';
import { BehaviorSubject, Subject } from 'rxjs';
import { EelDelegateService } from './eel-delegate.service';
import * as _ from 'lodash';

@Injectable({
  providedIn: 'root'
})
export class MainService {

  resourceData$: BehaviorSubject<ReadData | null> = new BehaviorSubject<ReadData | null>(null);
  resourceError$: BehaviorSubject<ReadError | null> = new BehaviorSubject<ReadError | null>(null);

  customActionRunning$: BehaviorSubject<boolean> = new BehaviorSubject<boolean>(false);

  readonly changedDataBlocks: { [key: string]: any } = {};
  dataBlockChange$: Subject<[string, any]> = new Subject<[string, any]>();

  constructor(readonly eelDelegate: EelDelegateService) {
    this.eelDelegate.openedResource$.subscribe((value) => {
      this.clearUnsavedChanges();
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
    this.dataBlockChange$.subscribe(([blockId, value]) => {
      if (value === undefined) { // change reverted
        delete this.changedDataBlocks[blockId];
      } else {
        this.changedDataBlocks[blockId] = value;
      }
    });
  }

  get hasUnsavedChanges(): boolean {
    return Object.keys(this.changedDataBlocks).length > 0;
  }

  clearUnsavedChanges() {
    Object.keys(this.changedDataBlocks).forEach(key => {
      delete this.changedDataBlocks[key];
    });
  }

  public async runCustomAction(readData: ReadData, action: CustomAction, args: { [key: string]: any }) {
    this.customActionRunning$.next(true);
    const res: ReadData | ReadError = await this.eelDelegate.runCustomAction(readData, action, args);
    if (!!(res as ReadError).error_class) {
      this.customActionRunning$.next(false);
      throw res;
    }
    _.merge(readData, res);
    this.changedDataBlocks['__custom_action_performed__'] = 1;
    this.customActionRunning$.next(false);
    return res;
  }
}
