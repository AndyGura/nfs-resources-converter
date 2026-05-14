import { Injectable, NgZone } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { BlockData, CustomAction, ReadError, Resource, ResourceError } from '../../components/editor/types';

declare const eel: { expose: (func: Function, alias: string) => void } & { [key: string]: Function; _websocket: any };

type GeneralConfig = {
  blender_executable: string;
  ffmpeg_executable: string;
  print_errors: boolean;
  print_blender_log: boolean;
  recent_files: string[];
  show_hidden_fields: boolean;
};

type ConversionConfig = {
  multiprocess_processes_count: number;
  input_path: string;
  output_path: string;
  images__save_images_only: boolean;
  maps__save_as_chunked: boolean;
  maps__save_invisible_wall_collisions: boolean;
  maps__save_terrain_collisions: boolean;
  maps__save_spherical_skybox_texture: boolean;
  maps__add_props_to_obj: boolean;
  geometry__save_obj: boolean;
  geometry__save_blend: boolean;
  geometry__export_to_gg_web_engine: boolean;
};

@Injectable()
export class ApiDelegateImplService {
  public readonly openedResource$: BehaviorSubject<Resource | ResourceError | null> = new BehaviorSubject<
    Resource | ResourceError | null
  >(null);
  public readonly openedResourcePath$: BehaviorSubject<string | null> = new BehaviorSubject<string | null>(null);
  public readonly recentFiles$: BehaviorSubject<string[]> = new BehaviorSubject<string[]>([]);
  public readonly conversionProgress$: BehaviorSubject<[number, number]> = new BehaviorSubject([0, 0]);
  public readonly version$: BehaviorSubject<string> = new BehaviorSubject<string>('');
  private callQueue: Promise<any> = Promise.resolve();

  constructor(private readonly ngZone: NgZone) {
    eel.expose(this.wrapHandler(this.openFile), 'open_file');
    eel.expose(this.wrapHandler(this.updateConversionProgress), 'update_conversion_progress');
    this.enqueue(() => eel['on_angular_ready']()()).then();
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

  private async enqueue<T>(task: () => Promise<T>): Promise<T> {
    const previous = this.callQueue;
    const current = (async () => {
      try {
        await previous;
      } catch (e) {
        // ignore
      }
      return await task();
    })();
    this.callQueue = current;
    return current;
  }

  private wrapHandler(handler: (...args: any[]) => unknown) {
    return (...args: any[]) => {
      try {
        NgZone.assertInAngularZone();
        handler.bind(this)(...args);
      } catch (err) {
        this.ngZone.run(handler, this, args);
      }
    };
  }

  public async openFile(path: string, forceReload: boolean = false) {
    return this.enqueue(async () => {
      if (!path) {
        return;
      }
      this.openedResource$.next(null);
      this.openedResourcePath$.next(path);
      const res: Omit<Resource, 'id'> | Omit<ResourceError, 'id'> = await eel['open_file'](path, forceReload)();
      this.openedResource$.next({ ...res, id: res['name'] });
      await this._syncRecentFiles();
    });
  }

  public async syncVersion() {
    return this.enqueue(async () => {
      const version = await eel['get_version']()();
      this.version$.next(version);
    });
  }

  public async syncRecentFiles() {
    return this.enqueue(() => this._syncRecentFiles());
  }

  private async _syncRecentFiles() {
    const cfg = await this._getGeneralConfig();
    return this.recentFiles$.next(cfg.recent_files || []);
  }

  updateConversionProgress(current: number, total: number): void {
    this.conversionProgress$.next([current, total]);
  }

  public async openFileDialog(multiple: boolean = false): Promise<string[]> {
    return await this.enqueue(() => eel['open_file_dialog'](multiple)());
  }

  public async saveFileDialog(fileName?: string): Promise<string | null> {
    return await this.enqueue(() => eel['save_file_dialog'](fileName || null)());
  }

  public async openFileWithSystemApp(path: string) {
    await this.enqueue(() => eel['open_file_with_system_app'](path)());
  }

  public async retrieveValue<T = any>(id: string): Promise<T> {
    return await this.enqueue(() => eel['retrieve_value'](id)());
  }

  public async runCustomAction(name: string, action: CustomAction, args: { [key: string]: any }) {
    return this.enqueue(() => eel['run_custom_action'](name, action, args)());
  }

  public async getNewItemData(id: string): Promise<any> {
    return this.enqueue(() => eel['get_new_item_data'](id)());
  }

  public async saveFile(changes: { id: string; value: any }[]): Promise<void> {
    return this.enqueue(async () => {
      const current = this.openedResource$.getValue();
      if (!current) return;
      const updatedData = await eel['save_file'](this.openedResourcePath$.getValue(), changes)();
      this.openedResource$.next({
        id: current.id,
        name: current.name,
        schema: current.schema,
        data: updatedData,
      });
    });
  }

  public async serializeResource(
    id: string,
    path: string | null = null,
    changes = [],
    settingsPatch: any = {},
  ): Promise<string[]> {
    return this.enqueue(() => eel['serialize_resource'](id, path, changes, settingsPatch)());
  }

  public async deserializeResource(
    id: string,
    filePaths: string[],
    extraOpts: any = {},
  ): Promise<BlockData | ReadError> {
    return this.enqueue(() => eel['deserialize_resource'](id, filePaths, extraOpts)());
  }

  public async selectDirectoryDialog(): Promise<string | null> {
    return await this.enqueue(() => eel['select_directory_dialog']()());
  }

  public async getGeneralConfig(): Promise<GeneralConfig> {
    return await this.enqueue(() => this._getGeneralConfig());
  }

  private async _getGeneralConfig(): Promise<GeneralConfig> {
    return await eel['get_general_config']()();
  }

  public async getConversionConfig(): Promise<ConversionConfig> {
    return await this.enqueue(() => eel['get_conversion_config']()());
  }

  public async patchGeneralConfig(data: Partial<GeneralConfig>): Promise<GeneralConfig> {
    return await this.enqueue(() => eel['patch_general_config'](data)());
  }

  public async patchConversionConfig(data: Partial<ConversionConfig>): Promise<ConversionConfig> {
    return await this.enqueue(() => eel['patch_conversion_config'](data)());
  }

  public async testExecutable(executablePath: string): Promise<any> {
    return await this.enqueue(() => eel['test_executable'](executablePath)());
  }

  public async convertFiles(
    inputPath: string,
    outputPath: string,
    settings?: any,
  ): Promise<{ success: boolean; error?: string; output_path?: string }> {
    return await this.enqueue(() => eel['convert_files'](inputPath, outputPath, settings)());
  }

  public async startFile(path: string): Promise<{ success: boolean; error?: string }> {
    return await this.enqueue(() => eel['start_file'](path)());
  }

  public async closeFile(): Promise<{ success: boolean; message: string }> {
    return this.enqueue(async () => {
      const result = await eel['close_file']()();
      if (result.success) {
        this.openedResource$.next(null);
        this.openedResourcePath$.next(null);
      }
      return result;
    });
  }
}
