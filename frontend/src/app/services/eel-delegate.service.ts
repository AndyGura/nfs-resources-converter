import { Injectable, NgZone } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

declare const eel: { expose: (func: Function, alias: string) => void } & { [key: string]: Function; _websocket: any };

@Injectable({
  providedIn: 'root',
})
export class EelDelegateService {
  public readonly openedResource$: BehaviorSubject<Resource | ResourceError | null> = new BehaviorSubject<
    Resource | ResourceError | null
  >(null);
  public readonly openedResourcePath$: BehaviorSubject<string | null> = new BehaviorSubject<string | null>(null);

  constructor(private readonly ngZone: NgZone) {
    eel.expose(this.wrapHandler(this.openFile), 'open_file');
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
}
