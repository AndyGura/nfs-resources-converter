import { Injectable } from '@angular/core';
import { BehaviorSubject, Subject } from 'rxjs';
import { EelDelegateService } from './eel-delegate.service';
import { cloneDeep, forOwn, isEqual, isObject, merge } from 'lodash';

@Injectable({
  providedIn: 'root'
})
export class MainService {

  private dataSnapshot: any;
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
        this.dataSnapshot = cloneDeep(this.buildResourceDataSnapshot((value as ReadData).value));
        this.resourceData$.next(value as ReadData);
        this.resourceError$.next(null);
      } else {
        this.resourceData$.next(null);
        this.resourceError$.next(value as ReadError);
      }
    });
    this.dataBlockChange$.subscribe(([blockId, value]) => {
      if (isEqual(value, this.getInitialValueFromSnapshot(blockId))) { // change reverted
        delete this.changedDataBlocks[blockId];
      } else {
        this.changedDataBlocks[blockId] = value;
      }
    });
  }

  get hasUnsavedChanges(): boolean {
    return Object.keys(this.changedDataBlocks).length > 0;
  }

  private getInitialValueFromSnapshot(blockId: string): any {
    let sub = this.dataSnapshot;
    const blockPath = blockId.replace('__', '/').split('/');
    for (let i = 0; i < blockPath.length - 1; i++) {
      sub = sub[blockPath[i]];
    }
    return sub[blockPath[blockPath.length - 1]];
  }

  private buildResourceDataSnapshot(readDataValue: any): { [key: string]: any } {
    const result: any = {};
    const recurse = (source: any) => {
      forOwn(source, (value) => {
        if (isObject(value)) {
          if (value && (value as any).block_class_mro) {
            const blockPath = (value as any).block_id.replace('__', '/').split('/');
            let sub = result;
            for (let i = 0; i < blockPath.length - 1; i++) {
              if (!sub[blockPath[i]] || !sub[blockPath[i]].__snap__) {
                sub[blockPath[i]] = { __snap__: true };
              }
              sub = sub[blockPath[i]];
            }
            sub[blockPath[blockPath.length - 1]] = (value as any).value;
          }
          recurse(value);
        }
      });
    }
    recurse(readDataValue);
    return result;
  }

  clearUnsavedChanges() {
    Object.keys(this.changedDataBlocks).forEach(key => {
      delete this.changedDataBlocks[key];
    });
  }

  private async processExternalChanges(call: () => Promise<ReadData | ReadError>): Promise<ReadData | ReadError> {
    this.customActionRunning$.next(true);
    const res: ReadData | ReadError = await call();
    if (!!(res as ReadError).error_class) {
      this.customActionRunning$.next(false);
      throw res;
    }
    merge(this.resourceData$.getValue()!, res);
    this.changedDataBlocks['__has_external_changes__'] = 1;
    this.customActionRunning$.next(false);
    return res;
  }

  public async runCustomAction(action: CustomAction, args: { [key: string]: any }) {
    return this.processExternalChanges(() => this.eelDelegate.runCustomAction(this.resourceData$.getValue()!, action, args));
  }

  public async deserializeResource(id: string) {
    return this.processExternalChanges(() => this.eelDelegate.deserializeResource(id));
  }
}
