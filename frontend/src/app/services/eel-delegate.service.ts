import { Injectable, NgZone } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

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

  public readonly conversionProgress$: BehaviorSubject<[number, number]> = new BehaviorSubject([0, 0]);

  constructor(private readonly ngZone: NgZone) {
    eel.expose(this.wrapHandler(this.openFile), 'open_file');
    eel.expose(this.wrapHandler(this.updateConversionProgress), 'update_conversion_progress');
    eel['on_angular_ready']();
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
      } catch (err) {
        this.ngZone.run(handler, this, args);
      }
    };
  }

  public async openFile(path: string, forceReload: boolean = false) {
    this.openedResource$.next(null);
    this.openedResourcePath$.next(path);
    const res: Omit<Resource, 'id'> | Omit<ResourceError, 'id'> = await eel['open_file'](path, forceReload)();
    this.openedResource$.next({ ...res, id: res.name });
  }

  updateConversionProgress(current: number, total: number): void {
    this.conversionProgress$.next([current, total]);
  }

  public async openFileDialog(): Promise<string | null> {
    return await eel['open_file_dialog']()();
  }

  public async openFileWithSystemApp(path: string) {
    await eel['open_file_with_system_app'](path)();
  }

  public async retrieveValue<T = any>(id: string): Promise<T> {
    return await eel['retrieve_value'](id)();
  }

  public async runCustomAction(name: string, action: CustomAction, args: { [key: string]: any }) {
    return eel['run_custom_action'](name, action, args)();
  }

  public async saveFile(changes: { id: string; value: any }[]): Promise<void> {
    const current = this.openedResource$.getValue();
    if (!current) return;
    const updatedData = await eel['save_file'](this.openedResourcePath$.getValue(), changes)();
    this.openedResource$.next({
      id: current.id,
      name: current.name,
      schema: current.schema,
      data: updatedData,
    });
  }

  public async serializeResource(id: string, settingsPatch: any = {}): Promise<string[]> {
    return eel['serialize_resource'](id, settingsPatch)();
  }

  public async serializeResourceTmp(
    id: string,
    changes: { id: string; value: any }[],
    settingsPatch: any = {},
  ): Promise<string[]> {
    return eel['serialize_resource_tmp'](id, changes, settingsPatch)();
  }

  public async serializeReversible(id: string, changes: { id: string; value: any }[]): Promise<[string[], boolean]> {
    return eel['serialize_reversible'](id, changes)();
  }

  public async deserializeResource(id: string): Promise<BlockData | ReadError> {
    return eel['deserialize_resource'](id)();
  }

  public async selectDirectoryDialog(): Promise<string | null> {
    return await eel['select_directory_dialog']()();
  }

  public async getGeneralConfig(): Promise<GeneralConfig> {
    return await eel['get_general_config']()();
  }

  public async getConversionConfig(): Promise<ConversionConfig> {
    return await eel['get_conversion_config']()();
  }

  public async patchGeneralConfig(data: Partial<GeneralConfig>): Promise<GeneralConfig> {
    return await eel['patch_general_config'](data)();
  }

  public async patchConversionConfig(data: Partial<ConversionConfig>): Promise<ConversionConfig> {
    return await eel['patch_conversion_config'](data)();
  }

  public async testExecutable(executablePath: string): Promise<any> {
    return await eel['test_executable'](executablePath)();
  }

  public async convertFiles(
    inputPath: string,
    outputPath: string,
    settings?: any,
  ): Promise<{ success: boolean; error?: string; output_path?: string }> {
    return await eel['convert_files'](inputPath, outputPath, settings)();
  }

  public async startFile(path: string): Promise<{ success: boolean; error?: string }> {
    return await eel['start_file'](path)();
  }

  public async closeFile(): Promise<{ success: boolean; message: string }> {
    const result = await eel['close_file']()();
    if (result.success) {
      this.openedResource$.next(null);
      this.openedResourcePath$.next(null);
    }
    return result;
  }
}
