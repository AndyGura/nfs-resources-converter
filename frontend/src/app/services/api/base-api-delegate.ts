import { MatDialog } from '@angular/material/dialog';
import { BehaviorSubject, Subject } from 'rxjs';
import { BlockData, CustomAction, ReadError, Resource, ResourceError } from '../../components/editor/types';
import { ErrorDialogComponent } from '../../components/error.dialog/error.dialog.component';
import { ChangeEntry, ChangesFeUpdate } from '../changes.service';
import { ConversionConfig, GeneralConfig } from './api-types';

export abstract class BaseApiDelegateService {
  private _implPromise: Promise<any> | null = null;
  protected _impl: any = null;

  // public state and events
  public readonly openedResource$: BehaviorSubject<Resource | ResourceError | null> = new BehaviorSubject<
    Resource | ResourceError | null
  >(null);
  public readonly openedResourcePath$: BehaviorSubject<string | null> = new BehaviorSubject<string | null>(null);
  public readonly recentFiles$: BehaviorSubject<string[]> = new BehaviorSubject<string[]>([]);
  public readonly version$: BehaviorSubject<string> = new BehaviorSubject<string>('');
  public readonly onFileOpened$: Subject<void> = new Subject<void>();

  // incoming calls handlers
  public readonly onAppendChanges$: Subject<[ChangeEntry[]]> = new Subject<[ChangeEntry[]]>();
  public readonly conversionProgress$: BehaviorSubject<[number, number]> = new BehaviorSubject<[number, number]>([
    0, 0,
  ]);

  protected constructor(protected readonly dialog: MatDialog) {}

  protected abstract initImpl(): Promise<any>;

  private async getImpl() {
    if (this._impl) return this._impl;
    if (!this._implPromise) {
      this._implPromise = this.initImpl();
      this._implPromise.then(impl => {
        this._impl = impl;
        this._implPromise = null;
        // public state and events
        this._impl.openedResource$.subscribe((v: any) => {
          if (this.openedResource$.getValue() !== v) this.openedResource$.next(v);
        });
        this._impl.openedResourcePath$.subscribe((v: any) => {
          if (this.openedResourcePath$.getValue() !== v) this.openedResourcePath$.next(v);
        });
        this._impl.recentFiles$.subscribe((v: any) => {
          if (this.recentFiles$.getValue() !== v) this.recentFiles$.next(v);
        });
        this._impl.version$.subscribe((v: any) => {
          if (this.version$.getValue() !== v) this.version$.next(v);
        });
        this._impl.onFileOpened$.subscribe(() => {
          this.onFileOpened$.next();
        });
        this._impl.apiError$.subscribe((message: string) => {
          this.dialog.open(ErrorDialogComponent, {
            data: { message },
          });
        });

        // incoming calls handlers
        this._impl.onAppendChanges$.subscribe((v: any) => {
          this.onAppendChanges$.next(v);
        });
        this._impl.conversionProgress$.subscribe((v: any) => {
          if (this.conversionProgress$.getValue() !== v) this.conversionProgress$.next(v);
        });
      });
    }
    return this._implPromise;
  }

  // File API
  public async openFile(path: string, forceReload: boolean = false) {
    return (await this.getImpl()).openFile(path, forceReload);
  }

  public async openFileWithSystemApp(path: string) {
    return (await this.getImpl()).openFileWithSystemApp(path);
  }

  public async saveFile(): Promise<void> {
    return (await this.getImpl()).saveFile();
  }

  public async createNewFile(path: string, format: string): Promise<Resource | ResourceError> {
    return (await this.getImpl()).createNewFile(path, format);
  }

  public async closeFile(): Promise<{ success: boolean; message: string }> {
    return (await this.getImpl()).closeFile();
  }

  // Resource API
  public async retrieveValue<T = any>(id: string): Promise<T> {
    return (await this.getImpl()).retrieveValue(id);
  }

  public async runCustomAction(name: string, action: CustomAction, args: { [key: string]: any }) {
    return (await this.getImpl()).runCustomAction(name, action, args);
  }

  public async getNewItemData(id: string, patch: any = {}): Promise<any> {
    return (await this.getImpl()).getNewItemData(id, patch);
  }

  // Serialization API
  public async serializeResource(
    blockId: string,
    path: string | null = null,
    settingsPatch: any = {},
  ): Promise<string[]> {
    return (await this.getImpl()).serializeResource(blockId, path, settingsPatch);
  }

  public async deserializeResource(
    id: string,
    filePaths: string[],
    extraOpts: any = {},
  ): Promise<BlockData | ReadError> {
    return (await this.getImpl()).deserializeResource(id, filePaths, extraOpts);
  }

  // Conversion API
  public async convertFiles(
    inputPath: string,
    outputPath: string,
    settings?: any,
  ): Promise<{ success: boolean; error?: string; output_path?: string }> {
    return (await this.getImpl()).convertFiles(inputPath, outputPath, settings);
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

  // Changes API
  public async getRevisions(): Promise<[number, number]> {
    return (await this.getImpl()).getRevisions();
  }

  public async getChanges(): Promise<ChangeEntry[]> {
    return (await this.getImpl()).getChanges();
  }

  public async onFeUpdate(updateDict: ChangesFeUpdate): Promise<void> {
    return (await this.getImpl()).onFeUpdate(updateDict);
  }

  // File dialog API
  public async openFileDialog(multiple: boolean = false): Promise<string[]> {
    return (await this.getImpl()).openFileDialog(multiple);
  }

  public async saveFileDialog(fileName?: string): Promise<string | null> {
    return (await this.getImpl()).saveFileDialog(fileName);
  }

  public async selectDirectoryDialog(): Promise<string | null> {
    return (await this.getImpl()).selectDirectoryDialog();
  }

  // shortcuts
  public async syncRecentFiles() {
    return (await this.getImpl()).syncRecentFiles();
  }

  public async syncVersion() {
    return (await this.getImpl()).syncVersion();
  }
}
