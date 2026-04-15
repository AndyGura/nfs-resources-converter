import { Injectable, NgZone } from '@angular/core';
import { BehaviorSubject, firstValueFrom } from 'rxjs';
import { BlockData, CustomAction, ReadError, Resource, ResourceError } from '../components/editor/types';

// These types are used by consumers of this service
export type GeneralConfig = {
  blender_executable: string;
  ffmpeg_executable: string;
  print_errors: boolean;
  print_blender_log: boolean;
};

export type ConversionConfig = {
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
  private _implPromise: Promise<any> | null = null;
  private _impl: any = null;

  public readonly openedResource$: BehaviorSubject<Resource | ResourceError | null> = new BehaviorSubject<
    Resource | ResourceError | null
  >(null);
  public readonly openedResourcePath$: BehaviorSubject<string | null> = new BehaviorSubject<string | null>(null);
  public readonly recentFiles$: BehaviorSubject<string[]> = new BehaviorSubject<string[]>([]);
  public readonly conversionProgress$: BehaviorSubject<[number, number]> = new BehaviorSubject<[number, number]>([0, 0]);
  public readonly version$: BehaviorSubject<string> = new BehaviorSubject<string>('');

  constructor(private readonly ngZone: NgZone) {
    this.initImpl().then();
  }

  private async initImpl() {
    if (!this._implPromise) {
      this._implPromise = import(/* webpackChunkName: "eel" */ './eel-delegate-impl/eel-delegate-impl.service').then(
        m => {
          this._impl = new m.EelDelegateImplService(this.ngZone);
          // Sync subjects from impl to this wrapper
          this._impl.openedResource$.subscribe((v: any) => {
            if (this.openedResource$.getValue() !== v) this.openedResource$.next(v);
          });
          this._impl.openedResourcePath$.subscribe((v: any) => {
            if (this.openedResourcePath$.getValue() !== v) this.openedResourcePath$.next(v);
          });
          this._impl.recentFiles$.subscribe((v: any) => {
            if (this.recentFiles$.getValue() !== v) this.recentFiles$.next(v);
          });
          this._impl.conversionProgress$.subscribe((v: any) => {
            if (this.conversionProgress$.getValue() !== v) this.conversionProgress$.next(v);
          });
          this._impl.version$.subscribe((v: any) => {
            if (this.version$.getValue() !== v) this.version$.next(v);
          });
          return this._impl;
        },
      );
    }
    return this._implPromise;
  }

  private async getImpl() {
    if (this._impl) return this._impl;
    return await this.initImpl();
  }

  public async openFile(path: string, forceReload: boolean = false) {
    return (await this.getImpl()).openFile(path, forceReload);
  }

  public async syncVersion() {
    return (await this.getImpl()).syncVersion();
  }

  public async syncRecentFiles() {
    return (await this.getImpl()).syncRecentFiles();
  }

  updateConversionProgress(current: number, total: number): void {
    this.getImpl().then(impl => impl.updateConversionProgress(current, total));
  }

  public async openFileDialog(): Promise<string | null> {
    return (await this.getImpl()).openFileDialog();
  }

  public async openFileWithSystemApp(path: string) {
    return (await this.getImpl()).openFileWithSystemApp(path);
  }

  public async retrieveValue<T = any>(id: string): Promise<T> {
    return (await this.getImpl()).retrieveValue(id);
  }

  public async runCustomAction(name: string, action: CustomAction, args: { [key: string]: any }) {
    return (await this.getImpl()).runCustomAction(name, action, args);
  }

  public async getNewItemData(id: string): Promise<any> {
    return (await this.getImpl()).getNewItemData(id);
  }

  public async saveFile(changes: { id: string; value: any }[]): Promise<void> {
    return (await this.getImpl()).saveFile(changes);
  }

  public async serializeResource(id: string, settingsPatch: any = {}): Promise<string[]> {
    return (await this.getImpl()).serializeResource(id, settingsPatch);
  }

  public async serializeResourceTmp(
    id: string,
    changes: { id: string; value: any }[],
    settingsPatch: any = {},
  ): Promise<string[]> {
    return (await this.getImpl()).serializeResourceTmp(id, changes, settingsPatch);
  }

  public async serializeReversible(id: string, changes: { id: string; value: any }[]): Promise<[string[], boolean]> {
    return (await this.getImpl()).serializeReversible(id, changes);
  }

  public async deserializeResource(id: string): Promise<BlockData | ReadError> {
    return (await this.getImpl()).deserializeResource(id);
  }

  public async selectDirectoryDialog(): Promise<string | null> {
    return (await this.getImpl()).selectDirectoryDialog();
  }

  public async getGeneralConfig(): Promise<GeneralConfig> {
    return (await this.getImpl()).getGeneralConfig();
  }

  public async getConversionConfig(): Promise<ConversionConfig> {
    return (await this.getImpl()).getConversionConfig();
  }

  public async patchGeneralConfig(data: Partial<GeneralConfig>): Promise<GeneralConfig> {
    return (await this.getImpl()).patchGeneralConfig(data);
  }

  public async patchConversionConfig(data: Partial<ConversionConfig>): Promise<ConversionConfig> {
    return (await this.getImpl()).patchConversionConfig(data);
  }

  public async testExecutable(executablePath: string): Promise<any> {
    return (await this.getImpl()).testExecutable(executablePath);
  }

  public async convertFiles(
    inputPath: string,
    outputPath: string,
    settings?: any,
  ): Promise<{ success: boolean; error?: string; output_path?: string }> {
    return (await this.getImpl()).convertFiles(inputPath, outputPath, settings);
  }

  public async startFile(path: string): Promise<{ success: boolean; error?: string }> {
    return (await this.getImpl()).startFile(path);
  }

  public async closeFile(): Promise<{ success: boolean; message: string }> {
    return (await this.getImpl()).closeFile();
  }
}
