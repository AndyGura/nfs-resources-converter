import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { ApiDelegateService } from './api/api-delegate.service';
import { findNestedObjects } from '../utils/find-nested-object';
import { CustomAction, Resource, ResourceError } from '../components/editor/types';
import { ChangesService } from './changes.service';

@Injectable({
  providedIn: 'root',
})
export class MainService {
  resource$: BehaviorSubject<Resource | null> = new BehaviorSubject<Resource | null>(null);
  error$: BehaviorSubject<ResourceError | null> = new BehaviorSubject<ResourceError | null>(null);

  customActionRunning$: BehaviorSubject<boolean> = new BehaviorSubject<boolean>(false);
  isSaving$: BehaviorSubject<boolean> = new BehaviorSubject<boolean>(false);

  public hideHiddenFields$: BehaviorSubject<boolean> = new BehaviorSubject<boolean>(true);
  public focusedResourceId$: BehaviorSubject<string | null> = new BehaviorSubject<string | null>(null);

  constructor(
    public readonly api: ApiDelegateService,
    public readonly changes: ChangesService,
  ) {
    this.api.getGeneralConfig().then(config => {
      this.hideHiddenFields$.next(!config.show_hidden_fields);
      this.hideHiddenFields$.subscribe(async hide => {
        const currentConfig = await this.api.getGeneralConfig();
        if (currentConfig.show_hidden_fields !== !hide) {
          await this.api.patchGeneralConfig({ show_hidden_fields: !hide });
        }
      });
    });
    this.api.openedResource$.subscribe(value => {
      this.changes.syncState().then();
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
  }

  public async runCustomAction(id: string, action: CustomAction, args: { [key: string]: any }) {
    this.customActionRunning$.next(true);
    try {
      await this.api.runCustomAction(id, action, args);
    } finally {
      this.customActionRunning$.next(false);
    }
  }

  public async deserializeResource(id: string, filePaths: string[], extraOpts: any = {}) {
    await this.api.deserializeResource(id, filePaths, extraOpts);
  }

  public async reloadResource() {
    const path = this.api.openedResourcePath$.getValue();
    if (path) {
      await this.api.openFile(path, true);
      this.changes.syncState().then();
    }
  }

  public async saveResource() {
    this.isSaving$.next(true);
    try {
      await this.api.saveFile();
      await this.changes.syncState();
    } finally {
      this.isSaving$.next(false);
    }
  }

  public async getNewItemData(id: string, kwargs: any = {}): Promise<any> {
    return this.api.getNewItemData(id, kwargs);
  }
}
