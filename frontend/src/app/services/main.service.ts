import { Injectable } from '@angular/core';
import { BehaviorSubject, Subject } from 'rxjs';
import { EelDelegateService } from './eel-delegate.service';
import { cloneDeep, forOwn, isEqual, isObject, merge } from 'lodash';

@Injectable({
  providedIn: 'root',
})
export class MainService {
  private dataSnapshot: any;
  resource$: BehaviorSubject<Resource | null> = new BehaviorSubject<Resource | null>(null);
  error$: BehaviorSubject<ResourceError | null> = new BehaviorSubject<ResourceError | null>(null);

  customActionRunning$: BehaviorSubject<boolean> = new BehaviorSubject<boolean>(false);

  readonly changedDataBlocks: { [key: string]: any } = {};
  dataBlockChange$: Subject<[string, any]> = new Subject<[string, any]>();

  public hideHiddenFields$: BehaviorSubject<boolean> = new BehaviorSubject<boolean>(true);

  constructor(readonly eelDelegate: EelDelegateService) {
    this.eelDelegate.openedResource$.subscribe(value => {
      this.clearUnsavedChanges();
      if (!value?.schema) {
        this.resource$.next(null);
        this.error$.next(null);
      } else if (value.data.error_class) {
        this.error$.next(value);
        this.resource$.next(null);
      } else {
        this.dataSnapshot = cloneDeep(this.buildResourceDataSnapshot(value));
        this.resource$.next(value);
        console.log(value);
        this.error$.next(null);
      }
    });
    this.dataBlockChange$.subscribe(([blockId, value]) => {
      if (isEqual(value, this.getInitialValueFromSnapshot(blockId))) {
        // change reverted
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
    return this.dataSnapshot[blockId];
  }

  private buildResourceDataSnapshot(res: Resource): { [key: string]: any } {
    const result: any = {};
    const recurse = (id: string, data: BlockData) => {
      let joinStr = id.includes('__') ? '/' : '__';
      if (data instanceof Array) {
        for (let i = 0; i < data.length; i++) {
          recurse(id + joinStr + i, data[i]);
        }
      } else if (isObject(data)) {
        for (const key in data) {
          recurse(id + joinStr + key, (data as any)[key]);
        }
      } else {
        result[id] = data;
      }
    };
    recurse(res.id, res.data);
    return result;
  }

  clearUnsavedChanges() {
    Object.keys(this.changedDataBlocks).forEach(key => {
      delete this.changedDataBlocks[key];
    });
  }

  private async processExternalChanges(call: () => Promise<BlockData | ReadError>): Promise<BlockData | ReadError> {
    this.customActionRunning$.next(true);
    const res: BlockData | ReadError = await call();
    if (!!(res as ReadError).error_class) {
      this.customActionRunning$.next(false);
      throw res;
    }
    merge(this.resource$.getValue()!, res);
    this.changedDataBlocks['__has_external_changes__'] = 1;
    this.customActionRunning$.next(false);
    return res;
  }

  public async runCustomAction(action: CustomAction, args: { [key: string]: any }) {
    return this.processExternalChanges(() =>
      this.eelDelegate.runCustomAction(this.resource$.getValue()!.name, action, args),
    );
  }

  public async deserializeResource(id: string) {
    return this.processExternalChanges(() => this.eelDelegate.deserializeResource(id));
  }
}
