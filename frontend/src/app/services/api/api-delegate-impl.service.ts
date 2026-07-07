import { Injectable, NgZone } from '@angular/core';
import { BehaviorSubject, Subject } from 'rxjs';
import {
  BlockData,
  BlockSchema,
  CustomAction,
  ReadError,
  Resource,
  ResourceError,
} from '../../components/editor/types';
import { ChangeEntry, ChangesFeUpdate } from '../changes.service';
import { ConversionConfig, GeneralConfig } from './api-types';
import { findNestedObjects } from '../../utils/find-nested-object';

declare const eel: { expose: (func: Function, alias: string) => void } & { [key: string]: Function; _websocket: any };

@Injectable()
export class ApiDelegateImplService {
  // public state and events
  public readonly openedResource$: BehaviorSubject<Resource | ResourceError | null> = new BehaviorSubject<
    Resource | ResourceError | null
  >(null);
  public readonly openedResourcePath$: BehaviorSubject<string | null> = new BehaviorSubject<string | null>(null);
  public readonly recentFiles$: BehaviorSubject<string[]> = new BehaviorSubject<string[]>([]);
  public readonly version$: BehaviorSubject<string> = new BehaviorSubject<string>('');
  public readonly onFileOpened$: Subject<void> = new Subject<void>();
  public readonly apiError$: Subject<string> = new Subject<string>();

  // incoming calls handlers
  public readonly openArgFile$: Subject<[string]> = new Subject<[string]>();
  public readonly onAppendChanges$: Subject<[ChangeEntry[]]> = new Subject<[ChangeEntry[]]>();
  public readonly conversionProgress$: BehaviorSubject<[number, number]> = new BehaviorSubject<[number, number]>([
    0, 0,
  ]);

  constructor(private readonly ngZone: NgZone) {
    eel.expose(this.wrapHandler(this.openArgFile$), 'open_arg_file');
    eel.expose(this.wrapHandler(this.conversionProgress$), 'update_conversion_progress');
    eel.expose(this.wrapHandler(this.onAppendChanges$), 'on_append_changes');

    this.openArgFile$.subscribe(async ([path]) => this.openFile(path));

    this.wrapCall('on_angular_ready').then();
    this.syncRecentFiles().then();
    this.syncVersion().then();

    // wait while eel websocket connection establishes and add a handler to close window when main python script stopped
    setTimeout(async () => {
      while (true) {
        if (eel._websocket) {
          eel._websocket.onclose = () => window.close();
          break;
        }
        await new Promise(r => setTimeout(r, 0));
      }
    }, 0);
  }

  // File API
  public async openFileDialog(multiple: boolean = false): Promise<string[]> {
    return this.wrapCall('open_file_dialog', multiple);
  }

  public async saveFileDialog(fileName?: string): Promise<string | null> {
    return this.wrapCall('save_file_dialog', fileName || null);
  }

  public async openFile(path: string, forceReload: boolean = false) {
    if (!path) {
      return;
    }
    this.openedResource$.next(null);
    this.openedResourcePath$.next(path);
    const res: Omit<Resource, 'id'> | Omit<ResourceError, 'id'> = await this.wrapCall('open_file', path, forceReload);
    if (res.schema) {
      this.fixRecursiveSchema(res.schema);
    }
    this.openedResource$.next({ ...res, id: res['name'] });
    this.onFileOpened$.next();
    await this.syncRecentFiles();
  }

  public async openFileWithSystemApp(path: string) {
    return this.wrapCall('open_file_with_system_app', path);
  }

  public async saveFile(): Promise<void> {
    const current = this.openedResource$.getValue();
    if (!current) return;
    const updatedData = await this.wrapCall('save_file', this.openedResourcePath$.getValue());
    this.openedResource$.next({
      id: current.id,
      name: current.name,
      schema: current.schema,
      data: updatedData,
    });
  }

  public async createNewFile(path: string, format: string) {
    await this.wrapCall('create_new_file', path, format);
    this.openedResource$.next(null);
    this.openedResourcePath$.next(path);
    const res: Omit<Resource, 'id'> | Omit<ResourceError, 'id'> = await this.wrapCall('open_file', path, true);
    if (res.schema) {
      this.fixRecursiveSchema(res.schema);
    }
    this.openedResource$.next({ ...res, id: res['name'] });
    this.onFileOpened$.next();
    await this.syncRecentFiles();
  }

  public async closeFile(): Promise<{ success: boolean; message: string }> {
    const result = await this.wrapCall('close_file');
    if (result.success) {
      this.openedResource$.next(null);
      this.openedResourcePath$.next(null);
    }
    return result;
  }

  // Resource API
  public async retrieveValue<T = any>(id: string): Promise<T> {
    return this.wrapCall('retrieve_value', id);
  }

  public async runCustomAction(name: string, action: CustomAction, args: { [key: string]: any }) {
    return this.wrapCall('run_custom_action', name, action, args);
  }

  public async getNewItemData(id: string, patch: any = {}): Promise<any> {
    return this.wrapCall('get_new_item_data', id, patch);
  }

  // Serialization API
  public async serializeResource(
    blockId: string,
    path: string | null = null,
    settingsPatch: any = {},
  ): Promise<string[]> {
    return this.wrapCall('serialize_resource', blockId, path, settingsPatch);
  }

  public async deserializeResource(
    id: string,
    filePaths: string[],
    extraOpts: any = {},
  ): Promise<BlockData | ReadError> {
    return this.wrapCall('deserialize_resource', id, filePaths, extraOpts);
  }

  // Conversion API
  public async selectDirectoryDialog(): Promise<string | null> {
    return this.wrapCall('select_directory_dialog');
  }

  public async convertFiles(
    inputPath: string,
    outputPath: string,
    settings?: any,
  ): Promise<{ success: boolean; error?: string; output_path?: string }> {
    return this.wrapCall('convert_files', inputPath, outputPath, settings);
  }

  public async getGeneralConfig(): Promise<GeneralConfig> {
    return this.wrapCall('get_general_config');
  }

  public async getConversionConfig(): Promise<ConversionConfig> {
    return this.wrapCall('get_conversion_config');
  }

  public async patchGeneralConfig(data: Partial<GeneralConfig>): Promise<GeneralConfig> {
    return this.wrapCall('patch_general_config', data);
  }

  public async patchConversionConfig(data: Partial<ConversionConfig>): Promise<ConversionConfig> {
    return this.wrapCall('patch_conversion_config', data);
  }

  public async testExecutable(executablePath: string): Promise<any> {
    return this.wrapCall('test_executable', executablePath);
  }

  // Changes API
  public async getRevisions(): Promise<[number, number]> {
    return this.wrapCall('get_revisions');
  }

  public async getChanges(): Promise<ChangeEntry[]> {
    return this.wrapCall('get_changes');
  }

  public async onFeUpdate(updateDict: ChangesFeUpdate): Promise<void> {
    return this.wrapCall('on_fe_update', updateDict);
  }

  // shortcuts
  public async syncRecentFiles() {
    const cfg = await this.getGeneralConfig();
    return this.recentFiles$.next(cfg.recent_files || []);
  }

  public async syncVersion() {
    const version = await this.wrapCall('get_version');
    this.version$.next(version);
  }

  // internal
  private fixRecursiveSchema(schema: BlockSchema) {
    const recursiveSchemas = findNestedObjects(schema, 'is_recursive_ref', true);
    for (const [val, path] of recursiveSchemas) {
      const blockClass = val.block_class_mro;
      let entry = schema;
      let valueToSet = entry.block_class_mro === blockClass ? entry : undefined;
      for (const key of path.slice(0, path.length - 1)) {
        if (!valueToSet && entry[key]?.['block_class_mro'] === blockClass) {
          valueToSet = entry[key];
        }
        entry = entry[key];
      }
      entry[path[path.length - 1]] = valueToSet;
    }
  }

  private callQueue: Promise<any> = Promise.resolve();

  private async wrapCall(funcName: string, ...args: any[]): Promise<any> {
    try {
      const previous = this.callQueue;
      const current = (async () => {
        try {
          await previous;
        } catch (e) {
          // ignore
        }
        return await eel[funcName](...args)();
      })();
      this.callQueue = current;
      return await current;
    } catch (err: any) {
      this.apiError$.next(err.message || err.errorText || err.toString());
      throw err;
    }
  }

  private wrapHandler(subj: Subject<any>): (...args: any[]) => void {
    return (...args: any[]) => {
      try {
        NgZone.assertInAngularZone();
        subj.next(args);
      } catch (err) {
        this.ngZone.run(() => subj.next(args));
      }
    };
  }
}
