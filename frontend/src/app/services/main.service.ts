import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, Subject } from 'rxjs';
import { EelDelegateService } from './eel-delegate.service';
import isEqual from 'lodash/isEqual';
import isNumber from 'lodash/isNumber';
import { findNestedObjects } from '../utils/find-nested-object';
import { BlockData, CustomAction, ReadError, Resource, ResourceError } from '../components/editor/types';

@Injectable({
  providedIn: 'root',
})
export class MainService {
  private readonly _hasUnsavedChanges$: BehaviorSubject<boolean> = new BehaviorSubject<boolean>(false);
  resource$: BehaviorSubject<Resource | null> = new BehaviorSubject<Resource | null>(null);
  error$: BehaviorSubject<ResourceError | null> = new BehaviorSubject<ResourceError | null>(null);

  customActionRunning$: BehaviorSubject<boolean> = new BehaviorSubject<boolean>(false);

  readonly changedDataBlocks: { [key: string]: any } = {};
  dataBlockChange$: Subject<[string, any]> = new Subject<[string, any]>();

  public hideHiddenFields$: BehaviorSubject<boolean> = new BehaviorSubject<boolean>(true);

  constructor(readonly eelDelegate: EelDelegateService) {
    this.eelDelegate.openedResource$.subscribe(value => {
      this.clearUnsavedChanges();
      if (value?.data.error_class) {
        this.error$.next(value);
        this.resource$.next(null);
      } else if (!value?.schema) {
        this.resource$.next(null);
        this.error$.next(null);
      } else {
        // fix recursive schema
        const recursiveSchemas = findNestedObjects(value.schema, 'is_recursive_ref', true);
        for (const [val, path] of recursiveSchemas) {
          const blockClass = val.block_class_mro;
          let entry = value.schema;
          let valueToSet = entry.block_class_mro === blockClass ? entry : undefined;
          for (const key of path.slice(0, path.length - 1)) {
            if (!valueToSet && entry[key]?.['block_class_mro'] === blockClass) {
              valueToSet = entry[key];
            }
            entry = entry[key];
          }
          entry[path[path.length - 1]] = valueToSet;
        }
        this.resource$.next(value);
        this.error$.next(null);
      }
    });
    this.dataBlockChange$.subscribe(async ([blockId, value]) => {
      this.changedDataBlocks[blockId] = value;
      this.updateUnsavedChanges();
      const originalValue = await this.eelDelegate.retrieveValue(blockId);
      // if was changed by another concurrent call during awaiting
      if (this.changedDataBlocks[blockId] != value) {
        return;
      }
      if (isNumber(value) ? Math.abs(value - originalValue) < 0.0000000001 : isEqual(value, originalValue)) {
        // change reverted
        delete this.changedDataBlocks[blockId];
        this.updateUnsavedChanges();
      }
    });
  }

  private updateUnsavedChanges() {
    this._hasUnsavedChanges$.next(Object.keys(this.changedDataBlocks).length > 0);
  }
  get hasUnsavedChanges$(): Observable<boolean> {
    return this._hasUnsavedChanges$.asObservable();
  }

  get hasUnsavedChanges(): boolean {
    return this._hasUnsavedChanges$.getValue();
  }

  clearUnsavedChanges() {
    Object.keys(this.changedDataBlocks).forEach(key => {
      delete this.changedDataBlocks[key];
    });
    this.updateUnsavedChanges();
  }

  private async processExternalChanges(id: string, call: () => Promise<BlockData | ReadError>): Promise<void> {
    this.customActionRunning$.next(true);
    const res: BlockData | ReadError = await call();
    if (!!(res as ReadError).error_class) {
      this.customActionRunning$.next(false);
      throw res;
    }
    if (this.resource$.getValue()!.id === id) {
      this.resource$.getValue()!.data = res;
    } else {
      let dataPath = id
        .substring(this.resource$.getValue()!.id.length)
        .replace('__', '/')
        .split('/')
        .filter(x => x);
      let data: any = this.resource$.getValue()!.data;
      for (const key of dataPath.slice(0, dataPath.length - 1)) {
        data = data[key] || data[+key];
      }
      let lastKey: any = dataPath[dataPath.length - 1];
      if (data[lastKey] === undefined && data[+lastKey] !== undefined) {
        lastKey = +lastKey;
      }
      data[lastKey] = res;
    }
    this.clearUnsavedChanges();
    this.changedDataBlocks['__has_external_changes__'] = 1;
    this.updateUnsavedChanges();
    this.customActionRunning$.next(false);
  }

  public async runCustomAction(id: string, action: CustomAction, args: { [key: string]: any }) {
    if (action.is_pure) {
      await this.eelDelegate.runCustomAction(id, action, args);
    } else {
      return this.processExternalChanges(id, () => this.eelDelegate.runCustomAction(id, action, args));
    }
  }

  public async deserializeResource(id: string) {
    return this.processExternalChanges(id, () => this.eelDelegate.deserializeResource(id));
  }

  public async reloadResource() {
    const path = this.eelDelegate.openedResourcePath$.getValue();
    if (path) {
      this.eelDelegate.openFile(path, true).then();
    }
  }

  public async saveResource() {
    const changes = Object.entries(this.changedDataBlocks).filter(([id, _]) => id != '__has_external_changes__');
    await this.eelDelegate.saveFile(
      changes.map(([id, value]) => {
        return { id, value };
      }),
    );
    this.clearUnsavedChanges();
  }
}
