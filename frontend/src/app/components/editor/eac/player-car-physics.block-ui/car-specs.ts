import { Directive, inject, Input, NgZone, OnDestroy, OnInit } from '@angular/core';
import { auditTime, filter, Subscription } from 'rxjs';
import { SubscribableGuiComponent } from '../../gui.component';
import { BlockData, BlockSchema } from '../../types';
import { joinId } from '../../../../utils/join-id';
import { ChangeEntry } from '../../../../services/changes.service';

// TNFS 24-bit angles: 0x1000000 = full turn
export const ANGLE_FULL = 0x1000000;
export const angleToDeg = (a: number) => (a * 360) / ANGLE_FULL;
export const degToAngle = (d: number) => Math.round((d * ANGLE_FULL) / 360);

export const MPS_TO_KMH = 3.6;
export const MPS_TO_MPH = 2.2369363;
export const KW_TO_HP = 1.3410221;
export const G = 9.81;
// physics ticks per second
export const TICKS = 30;

export const powerKw = (torqueNm: number, rpm: number) => (torqueNm * rpm) / 9549.2966;

// the game's 8.8 fixed point inverse, rounded down (`force_to_accel` = floor_8(1 / `thrust_scale`))
export const floor8Inverse = (v: number) => (v ? Math.floor(256 / v) / 256 : 0);

export const GEAR_COLORS = ['#3f51b5', '#e91e63', '#009688', '#ff9800', '#9c27b0', '#795548', '#00acc1', '#8bc34a'];

export const ordinal = (n: number) => {
  const s = ['th', 'st', 'nd', 'rd'];
  const v = n % 100;
  return n + (s[(v - 20) % 10] || s[v] || s[0]);
};

export const fmt = (v: number, digits: number = 1) =>
  isFinite(v) ? v.toLocaleString('en-US', { maximumFractionDigits: digits, minimumFractionDigits: 0 }) : '–';

// Base of the TNFS car spec editors: tracks every change under the resource (charts, embedded field editors,
// undo / redo) to rebuild the derived view, and writes edits as single undoable changes
@Directive()
export abstract class CarSpecEditorBase
  extends SubscribableGuiComponent<{ [key: string]: any }>
  implements OnInit, OnDestroy
{
  private readonly zone = inject(NgZone);
  private changesSub?: Subscription;

  override get resourceData(): { [key: string]: any } | undefined {
    return super.resourceData;
  }

  @Input()
  override set resourceData(value: { [key: string]: any } | undefined) {
    super.resourceData = value;
    if (value) this.refresh();
  }

  override get resourceSchema(): BlockSchema | undefined {
    return super.resourceSchema;
  }

  @Input()
  override set resourceSchema(value: BlockSchema | undefined) {
    super.resourceSchema = value;
    this.descriptions = {};
    for (const f of value?.fields || []) this.descriptions[f.name] = f.description || '';
  }

  descriptions: { [field: string]: string } = {};

  ngOnInit(): void {
    this.changesSub = this.changes.change$
      .pipe(
        filter(id => !!this.resourceId && id.startsWith(this.resourceId)),
        auditTime(20),
      )
      .subscribe(() =>
        this.zone.run(() => {
          if (this.resourceData) this.refresh();
          this.cdr.markForCheck();
        }),
      );
  }

  override ngOnDestroy(): void {
    this.changesSub?.unsubscribe();
    super.ngOnDestroy();
  }

  // the change$ stream above already covers every nested id
  protected override subscriptionKeys(resourceId: string): string[] {
    return [];
  }

  protected abstract refresh(): void;

  protected get d(): BlockData {
    return this.resourceData!;
  }

  // sets several values (paths relative to the resource) as one undo step
  protected setValues(entries: [(string | number)[], any][]) {
    if (!this.resourceId || this.disabled) return;
    const changes: ChangeEntry[] = [];
    for (const [path, value] of entries) {
      let old: any = this.resourceData;
      for (const p of path) old = old?.[p];
      if (JSON.stringify(old) === JSON.stringify(value)) continue;
      changes.push({
        timestamp: Date.now(),
        op: 'set',
        id: joinId(this.resourceId, ...path),
        oldValue: old,
        newValue: value,
      });
    }
    if (changes.length === 1) {
      this.changes.appendChanges(changes[0]).then();
    } else if (changes.length > 1) {
      this.changes.appendChanges({ timestamp: Date.now(), op: 'bundle', id: this.resourceId, changes }).then();
    }
  }

  protected setValue(path: (string | number)[], value: any) {
    this.setValues([[path, value]]);
  }

  setField(name: string, value: any) {
    this.setValue([name], value);
  }

  onNumberInput(path: (string | number)[], raw: string, integer: boolean = false) {
    const v = parseFloat(raw);
    if (!isFinite(v)) return;
    this.setValue(path, integer ? Math.round(v) : v);
  }
}
