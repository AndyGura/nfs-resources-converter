import { Injectable, NgZone } from '@angular/core';
import { ApiDelegateService } from './api/api-delegate.service';
import { BehaviorSubject, Subject } from 'rxjs';
import { Resource } from '../components/editor/types';
import { SubscribableGuiComponent } from '../components/editor/gui.component';
import { splitLastIdPart } from '../utils/join-id';

export type ChangesFeUpdate = {
  newLocalRevision: number;
  newChanges: ChangeEntry[];
  poppedChanges: number;
};

export type ChangeEntry = {
  id: string;
  timestamp: number;
} & ChangeEntryPayload;

export type ChangeEntryPayload =
  | {
      op: 'set';
      oldValue: any;
      newValue: any;
    }
  | {
      op: 'array_insert';
      index: number;
      value: any;
    }
  | {
      op: 'array_remove';
      index: number;
      oldValue: any;
    }
  | {
      op: 'array_swap';
      indexA: number;
      indexB: number;
    };

class ChangeExecutor {
  private static locateId(resource: Resource, id: string): any {
    if (!resource) throw new Error('No resource opened');
    if (resource.id === id) {
      throw new Error('Cannot apply change to the top-level resource');
    }
    let dataPath = id
      .substring(resource.id.length)
      .replace('__', '/')
      .split('/')
      .filter(x => x);
    let data: any = resource.data;
    for (const key of dataPath) {
      data = data[key] || data[+key];
    }
    return data;
  }

  private static setResourceValue(resource: Resource, id: string, value: any) {
    const [superId, lastKey] = splitLastIdPart(id);
    const data = ChangeExecutor.locateId(resource, superId);
    if (data[lastKey] === undefined && data[+lastKey] !== undefined) {
      data[+lastKey] = value;
    } else {
      data[lastKey] = value;
    }
  }

  public static applyChange(api: ApiDelegateService, change: ChangeEntry): string[] {
    console.log(`Applying change: ${JSON.stringify(change)}`);
    let res = api.openedResource$.getValue() as Resource;
    if (change.op === 'set') {
      ChangeExecutor.setResourceValue(res, change.id, change.newValue);
      return [change.id];
    } else if (change.op == 'array_insert') {
      let array = ChangeExecutor.locateId(res, change.id);
      array.splice(change.index, 0, change.value);
      return [change.id];
    } else if (change.op == 'array_remove') {
      let array = ChangeExecutor.locateId(res, change.id);
      array.splice(change.index, 1);
      return [change.id];
    } else if (change.op == 'array_swap') {
      let array = ChangeExecutor.locateId(res, change.id);
      let tmp = array[change.indexA];
      array[change.indexA] = array[change.indexB];
      array[change.indexB] = tmp;
      return [change.id];
    } else {
      throw new Error('Unknown change operation: ' + (change as any).op);
    }
  }

  public static revertChange(api: ApiDelegateService, change: ChangeEntry): string[] {
    console.log(`Reverting change: ${JSON.stringify(change)}`);
    let res = api.openedResource$.getValue() as Resource;
    if (change.op === 'set') {
      ChangeExecutor.setResourceValue(res, change.id, change.oldValue);
      return [change.id];
    } else if (change.op == 'array_insert') {
      let array = ChangeExecutor.locateId(res, change.id);
      array.splice(change.index, 1);
      return [change.id];
    } else if (change.op == 'array_remove') {
      let array = ChangeExecutor.locateId(res, change.id);
      array.splice(change.index, 0, change.oldValue);
      return [change.id];
    } else if (change.op == 'array_swap') {
      let array = ChangeExecutor.locateId(res, change.id);
      let tmp = array[change.indexA];
      array[change.indexA] = array[change.indexB];
      array[change.indexB] = tmp;
      return [change.id];
    } else {
      throw new Error('Unknown change operation: ' + (change as any).op);
    }
  }
}

@Injectable({
  providedIn: 'root',
})
export class ChangesService {
  private _changes: ChangeEntry[] = [];
  private _localRevision: number = 0;
  private _fileRevision: number = 0;
  private _cdrSubscribers: { [id: string]: SubscribableGuiComponent } = {};
  public change$: Subject<string> = new Subject();

  public hasUnsavedChanges$: BehaviorSubject<boolean> = new BehaviorSubject(false);
  public isUndoAvailable$: BehaviorSubject<boolean> = new BehaviorSubject(false);
  public isRedoAvailable$: BehaviorSubject<boolean> = new BehaviorSubject(false);

  public get changes(): ChangeEntry[] {
    return this._changes;
  }

  public get localRevision(): number {
    return this._localRevision;
  }

  public get fileRevision(): number {
    return this._fileRevision;
  }

  constructor(
    private readonly api: ApiDelegateService,
    private readonly ngZone: NgZone,
  ) {
    this.api.onAppendChanges$.subscribe((changes: ChangeEntry[]) => {
      if (this._localRevision < this._changes.length) {
        this._changes.splice(this._localRevision);
      }
      this._changes.push(...changes);
      this.refreshRevisions().then();
    });
    this.api.onFileOpened$.subscribe(() => {
      this.clear();
    });
    (window as any).cdrSubscribers = this._cdrSubscribers;
  }

  public async syncState() {
    let changes = await this.api.getChanges();
    let [fr, lr] = await this.api.getRevisions();
    this._changes = changes;
    this._fileRevision = fr;
    this._localRevision = lr;
    this.hasUnsavedChanges$.next(this._fileRevision !== this._localRevision);
    this.isUndoAvailable$.next(this._localRevision > 0);
    this.isRedoAvailable$.next(this._localRevision < this._changes.length);
  }

  private async refreshRevisions() {
    let [fr, lr] = await this.api.getRevisions();
    if (this._fileRevision !== fr || this._localRevision !== lr) {
      console.warn('Changes revisions out of sync');
    }
    this._fileRevision = fr;
    this._localRevision = lr;
    this.hasUnsavedChanges$.next(this._fileRevision !== this._localRevision);
    this.isUndoAvailable$.next(this._localRevision > 0);
    this.isRedoAvailable$.next(this._localRevision < this._changes.length);
  }

  public async appendChanges(...newChanges: ChangeEntry[]): Promise<void> {
    let poppedChanges = this.changes.length - this._localRevision;
    if (poppedChanges > 0) {
      this._changes.splice(this._localRevision);
    }
    this._changes.push(...newChanges);
    this._localRevision = this.changes.length;
    let affectedIds: Set<string> = new Set();
    for (const change of newChanges) {
      for (const id of ChangeExecutor.applyChange(this.api, change)) {
        affectedIds.add(id);
      }
    }
    this.notifyUi(Array.from(affectedIds));
    await this.api.onFeUpdate({
      newLocalRevision: this._localRevision,
      newChanges: newChanges,
      poppedChanges: poppedChanges,
    });
    this.refreshRevisions().then();
  }

  public clear() {
    this._changes = [];
    this._localRevision = 0;
    this._fileRevision = 0;
    this.hasUnsavedChanges$.next(false);
    this.isUndoAvailable$.next(false);
    this.isRedoAvailable$.next(false);
  }

  public async undo(): Promise<void> {
    if (this._localRevision === 0) return;
    let affectedIds = ChangeExecutor.revertChange(this.api, this.changes[this._localRevision - 1]);
    this._localRevision -= 1;
    await this.api.onFeUpdate({
      newLocalRevision: this._localRevision,
      newChanges: [],
      poppedChanges: 0,
    });
    await this.refreshRevisions();
    this.notifyUi(affectedIds);
  }

  public async redo(): Promise<void> {
    if (this._localRevision === this._changes.length) return;
    let affectedIds = ChangeExecutor.applyChange(this.api, this.changes[this._localRevision]);
    this._localRevision += 1;
    await this.api.onFeUpdate({
      newLocalRevision: this._localRevision,
      newChanges: [],
      poppedChanges: 0,
    });
    await this.refreshRevisions();
    this.notifyUi(affectedIds);
  }

  private notifyUi(blockIds: string[]) {
    for (const blockId of blockIds) {
      let subscriptionId = Object.keys(this._cdrSubscribers)
        .filter(id => blockId.startsWith(id))
        .reduce<string | null>((prev, cur) => {
          if (!blockId.startsWith(cur) || (prev && prev.length > cur.length)) return prev;
          return cur;
        }, null);
      if (subscriptionId !== null) {
        this.ngZone.run(() => {
          this._cdrSubscribers[subscriptionId!].onExternalChanges();
        });
      }
      this.change$.next(blockId);
    }
  }

  public subscribeComponent(resourceId: string, component: SubscribableGuiComponent) {
    this._cdrSubscribers[resourceId] = component;
    console.log('CDR new subscriber for ' + resourceId + ': ', Object.keys(this._cdrSubscribers).length);
  }

  public unsubscribeComponent(resourceId: string) {
    delete this._cdrSubscribers[resourceId];
    console.log('CDR unsubscribed ' + resourceId);
  }
}
