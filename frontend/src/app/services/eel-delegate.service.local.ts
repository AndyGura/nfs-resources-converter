import { Injectable, NgZone } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { BehaviorSubject } from 'rxjs';
import { BlockData, CustomAction, ReadError, Resource, ResourceError } from '../components/editor/types';
import { ErrorDialogComponent } from '../components/error.dialog/error.dialog.component';

declare const eel: { expose: (func: Function, alias: string) => void } & { [key: string]: Function; _websocket: any };

type GeneralConfig = {
  blender_executable: string;
  ffmpeg_executable: string;
  print_errors: boolean;
  print_blender_log: boolean;
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

@Injectable({
  providedIn: 'root',
})
export class EelDelegateService {
  public readonly openedResource$: BehaviorSubject<Resource | ResourceError | null> = new BehaviorSubject<
    Resource | ResourceError | null
  >(null);
  public readonly openedResourcePath$: BehaviorSubject<string | null> = new BehaviorSubject<string | null>(null);
  public readonly recentFiles$: BehaviorSubject<string[]> = new BehaviorSubject<string[]>([]);
  public readonly conversionProgress$: BehaviorSubject<[number, number]> = new BehaviorSubject([0, 0]);
  public readonly version$: BehaviorSubject<string> = new BehaviorSubject<string>('');

  public changedDataBlocks: { [key: string]: any } = {};

  constructor(private readonly ngZone: NgZone, private readonly dialog: MatDialog) {
    eel.expose(this.wrapHandler(this.openFile), 'open_file');
    eel.expose(this.wrapHandler(this.updateConversionProgress), 'update_conversion_progress');
    eel['on_angular_ready']();
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

  private wrapHandler(handler: (...args: any[]) => unknown) {
    return (...args: any[]) => {
      try {
        NgZone.assertInAngularZone();
        handler.bind(this)(...args);
      } catch (err: any) {
        this.ngZone.run(() => {
          try {
            handler.bind(this)(...args);
          } catch (innerErr: any) {
            this.dialog.open(ErrorDialogComponent, {
              data: { message: innerErr.message || innerErr.errorText || innerErr.toString() },
            });
            throw innerErr;
          }
        });
      }
    };
  }

  private async runSafe<T>(func: () => Promise<T>): Promise<T> {
    try {
      return await func();
    } catch (err: any) {
      this.dialog.open(ErrorDialogComponent, {
        data: { message: err.message || err.errorText || err.toString() },
      });
      throw err;
    }
  }

  public async openFile(path: string, forceReload: boolean = false) {
    return this.runSafe(async () => {
      if (!path) {
        return;
      }
      this.openedResource$.next(null);
      this.openedResourcePath$.next(path);
      const res: Omit<Resource, 'id'> | Omit<ResourceError, 'id'> = await eel['open_file'](path, forceReload)();
      this.openedResource$.next({ ...res, id: res.name });
      await this.syncRecentFiles();
    });
  }

  public async syncVersion() {
    return this.runSafe(async () => {
      const version = await eel['get_version']()();
      this.version$.next(version);
    });
  }

  public async syncRecentFiles() {
    return this.runSafe(async () => {
      const files = await eel['get_recent_files']()();
      this.recentFiles$.next(files);
    });
  }

  updateConversionProgress(current: number, total: number): void {
    try {
      this.conversionProgress$.next([current, total]);
    } catch (err: any) {
      this.dialog.open(ErrorDialogComponent, {
        data: { message: err.message || err.errorText || err.toString() },
      });
      throw err;
    }
  }

  public async openFileDialog(multiple: boolean = false): Promise<string[]> {
    return this.runSafe(async () => await eel['open_file_dialog'](multiple)());
  }

  public async saveFileDialog(fileName?: string): Promise<string | null> {
    return this.runSafe(async () => await eel['save_file_dialog'](fileName || null)());
  }

  public async openFileWithSystemApp(path: string) {
    return this.runSafe(async () => {
      await eel['open_file_with_system_app'](path)();
    });
  }

  public async retrieveValue<T = any>(id: string): Promise<T> {
    return this.runSafe(async () => await eel['retrieve_value'](id)());
  }

  public async runCustomAction(name: string, action: CustomAction, args: { [key: string]: any }) {
    return this.runSafe(async () => eel['run_custom_action'](name, action, args)());
  }

  public async getNewItemData(id: string): Promise<any> {
    return this.runSafe(async () => eel['get_new_item_data'](id)());
  }

  public async saveFile(changes: { id: string; value: any }[]): Promise<void> {
    return this.runSafe(async () => {
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

  public async serializeResource(blockId: string, path: string | null = null, settingsPatch: any = {}): Promise<string[]> {
    let changes = Object.entries(this.changedDataBlocks)
      .filter(([id, _]) => id != '__has_external_changes__' && id.startsWith(blockId))
      .map(([id, value]) => {
        return { id, value };
      });
    return this.runSafe(async () => eel['serialize_resource'](blockId, path, changes, settingsPatch)());
  }

  public async deserializeResource(id: string, filePaths: string[], extraOpts: any = {}): Promise<BlockData | ReadError> {
    return this.runSafe(async () => eel['deserialize_resource'](id, filePaths, extraOpts)());
  }

  public async selectDirectoryDialog(): Promise<string | null> {
    return this.runSafe(async () => await eel['select_directory_dialog']()());
  }

  public async getGeneralConfig(): Promise<GeneralConfig> {
    return this.runSafe(async () => await eel['get_general_config']()());
  }

  public async getConversionConfig(): Promise<ConversionConfig> {
    return this.runSafe(async () => await eel['get_conversion_config']()());
  }

  public async patchGeneralConfig(data: Partial<GeneralConfig>): Promise<GeneralConfig> {
    return this.runSafe(async () => await eel['patch_general_config'](data)());
  }

  public async patchConversionConfig(data: Partial<ConversionConfig>): Promise<ConversionConfig> {
    return this.runSafe(async () => await eel['patch_conversion_config'](data)());
  }

  public async testExecutable(executablePath: string): Promise<any> {
    return this.runSafe(async () => await eel['test_executable'](executablePath)());
  }

  public async convertFiles(
    inputPath: string,
    outputPath: string,
    settings?: any,
  ): Promise<{ success: boolean; error?: string; output_path?: string }> {
    return this.runSafe(async () => await eel['convert_files'](inputPath, outputPath, settings)());
  }

  public async startFile(path: string): Promise<{ success: boolean; error?: string }> {
    return this.runSafe(async () => await eel['start_file'](path)());
  }

  public async closeFile(): Promise<{ success: boolean; message: string }> {
    return this.runSafe(async () => {
      const result = await eel['close_file']()();
      if (result.success) {
        this.openedResource$.next(null);
        this.openedResourcePath$.next(null);
      }
      return result;
    });
  }
}
