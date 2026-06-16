import { ChangeDetectorRef, Directive, inject, Input, OnDestroy } from '@angular/core';
import { BlockData, BlockSchema } from './types';
import { ChangeEntryPayload, ChangesService } from '../../services/changes.service';
import { MainService } from '../../services/main.service';
import { joinId } from '../../utils/join-id';

@Directive()
// TODO currently in progress: check all direct children, swithc them to use SubscribableGuiComponent
export abstract class GuiComponent<BD extends BlockData = BlockData> {
  readonly mainService = inject(MainService);
  readonly changes = inject(ChangesService);

  // inputs
  protected _resourceId?: string;
  protected _resourceName?: string;
  protected _resourceSchema?: BlockSchema;
  protected _resourceData?: BD;
  protected _resourceDescription?: string;
  protected _hideName?: boolean;
  protected _hideBlockActions?: boolean;
  protected _disabled?: boolean;

  public get resourceId(): string | undefined {
    return this._resourceId;
  }

  public get resourceName(): string | undefined {
    return this._resourceName;
  }

  public get resourceSchema(): BlockSchema | undefined {
    return this._resourceSchema;
  }

  public get resourceData(): BD | undefined {
    return this._resourceData;
  }

  public get resourceDescription(): string | undefined {
    return this._resourceDescription;
  }

  public get hideName(): boolean | undefined {
    return this._hideName;
  }

  public get hideBlockActions(): boolean | undefined {
    return this._hideBlockActions;
  }

  public get disabled(): boolean | undefined {
    return this._disabled;
  }

  @Input() public set resourceId(value: string | undefined) {
    this._resourceId = value;
  }

  @Input() public set resourceName(value: string | undefined) {
    this._resourceName = value;
  }

  @Input() public set resourceSchema(value: BlockSchema | undefined) {
    this._resourceSchema = value;
  }

  @Input() public set resourceData(value: BD | undefined) {
    this._resourceData = value;
  }

  @Input() public set resourceDescription(value: string | undefined) {
    this._resourceDescription = value;
  }

  @Input() public set hideName(value: boolean | undefined) {
    this._hideName = value;
  }

  @Input() public set hideBlockActions(value: boolean | undefined) {
    this._hideBlockActions = value;
  }

  @Input() public set disabled(value: boolean | undefined) {
    this._disabled = value;
  }
}

// Data GUI component that wants cdr to be triggered whenever data is changed by undo/redo/python
@Directive()
export abstract class SubscribableGuiComponent<BD extends BlockData = BlockData>
  extends GuiComponent<BD>
  implements OnDestroy
{
  readonly cdr = inject(ChangeDetectorRef);

  override get resourceId(): string | undefined {
    return super.resourceId;
  }

  @Input()
  override set resourceId(value: string | undefined) {
    if (super.resourceId === value) return;
    if (super.resourceId) {
      this.changes.unsubscribeComponent(super.resourceId);
    }
    super.resourceId = value;
    if (super.resourceId) {
      this.changes.subscribeComponent(super.resourceId, this);
    }
  }

  ngOnDestroy(): void {
    if (this._resourceId) {
      this.changes.unsubscribeComponent(this._resourceId);
    }
  }

  public onExternalChanges() {
    this.cdr.markForCheck();
  }

  public emitNewChange(change: ChangeEntryPayload & { id?: string }) {
    this.changes
      .appendChanges({
        timestamp: Date.now(),
        id: this.resourceId!,
        ...change,
      })
      .then();
  }

  public onValueSet(newValue: any, ...path: (string | number)[]) {
    let oldValue: any = this.resourceData;
    for (const p of path) {
      if (oldValue === undefined || oldValue === null) break;
      oldValue = oldValue[p];
    }
    this.emitNewChange({
      op: 'set',
      id: joinId(this.resourceId!, ...path),
      oldValue: oldValue,
      newValue: newValue,
    });
  }

  onFocus(...path: (string | number)[]) {
    if (this.resourceId) {
      this.mainService.focusedResourceId$.next(joinId(this.resourceId, ...path));
    }
  }

  onBlur(...path: (string | number)[]) {
    if (
      this.resourceId &&
      this.mainService.focusedResourceId$.getValue()?.startsWith(joinId(this.resourceId, ...path))
    ) {
      this.mainService.focusedResourceId$.next(null);
    }
  }
}

// Primitive type GUI component. It does not change data in place but emits new data
@Directive()
export abstract class PrimitiveGuiComponent<BD extends BlockData = BlockData> extends GuiComponent<BD> {
  public onValueSet(newValue: BD) {
    this.changes
      .appendChanges({
        timestamp: Date.now(),
        op: 'set',
        id: this.resourceId!,
        oldValue: this.resourceData ?? null,
        newValue: newValue,
      })
      .then();
  }

  onFocus() {
    if (this.resourceId) {
      this.mainService.focusedResourceId$.next(this.resourceId);
    }
  }

  onBlur() {
    if (this.mainService.focusedResourceId$.getValue() === this.resourceId) {
      this.mainService.focusedResourceId$.next(null);
    }
  }
}
