import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { ApiDelegateService } from './api/api-delegate.service';
import { CustomAction, Resource, ResourceError } from '../components/editor/types';
import { ChangesService } from './changes.service';
import { isLazyStub, LAZY_MARKER } from '../utils/lazy';

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

  // lazy parts being loaded, by id: one backend call per part however many components show it
  private readonly lazyLoads: Map<string, Promise<void>> = new Map();

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
        this.resource$.next(value);
        this.error$.next(null);
      }
    });
  }

  /**
   * Makes sure a lazy part of the opened resource is loaded. The backend parses it and the stub object is filled in
   * place, so every reference to it in the data tree sees the loaded data. Resolves at once for anything else
   */
  public async ensureLoaded(id: string, stub: any): Promise<void> {
    if (!isLazyStub(stub)) return;
    let load = this.lazyLoads.get(id);
    if (!load) {
      load = this.api.loadLazyPart(id).then(loaded => {
        if (!isLazyStub(stub)) return;
        for (const key of Object.keys(stub)) {
          delete stub[key];
        }
        Object.assign(stub, loaded);
        delete stub[LAZY_MARKER];
      });
      this.lazyLoads.set(id, load);
      load.finally(() => this.lazyLoads.delete(id)).catch(() => {});
    }
    return load;
  }

  public async runCustomAction(id: string, action: CustomAction, args: { [key: string]: any }) {
    this.customActionRunning$.next(true);
    try {
      await this.api.runCustomAction(id, action, args);
    } finally {
      this.customActionRunning$.next(false);
    }
  }

  // returns what the import did, for the user, when the importer tells it (folder import into a SHPI)
  public async deserializeResource(id: string, filePaths: string[], extraOpts: any = {}): Promise<string | null> {
    const result = await this.api.deserializeResource(id, filePaths, extraOpts);
    return result?.report ?? null;
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
      await this.changes.settled();
      await this.api.saveFile();
      await this.changes.syncState();
    } finally {
      this.isSaving$.next(false);
    }
  }

  public async getNewItemData(id: string, patch: any = {}): Promise<any> {
    return this.api.getNewItemData(id, patch);
  }

  public async getTrailingOptionalFieldData(id: string): Promise<any> {
    return this.api.getTrailingOptionalFieldData(id);
  }
}
