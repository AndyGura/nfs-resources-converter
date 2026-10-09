import { ChangeDetectionStrategy, ChangeDetectorRef, Component, ElementRef, OnDestroy, ViewChild } from '@angular/core';
import { BehaviorSubject, Subscription } from 'rxjs';
import { PrimitiveGuiComponent } from '../../gui.component';

export type AngleUnit = 'deg' | 'rad';

const UNIT_STORAGE_KEY = 'angleUnit';
const TWO_PI = Math.PI * 2;

const loadUnit = (): AngleUnit => {
  try {
    return localStorage.getItem(UNIT_STORAGE_KEY) === 'rad' ? 'rad' : 'deg';
  } catch {
    return 'deg';
  }
};

// Angle field: a dial to drag and a number in degrees or radians (the unit is shared by every angle field and
// remembered). Data is radians (`Nfs1Angle8`, `Nfs1Angle14`) or, when the schema has `angle_full_turn`, the plain
// integer the game stores (`IntegerAngleBlock`)
@Component({
  selector: 'app-angle-block-ui',
  templateUrl: './angle.block-ui.component.html',
  styleUrls: ['./angle.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  standalone: false,
})
export class AngleBlockUiComponent extends PrimitiveGuiComponent<number> implements OnDestroy {
  static readonly unit$ = new BehaviorSubject<AngleUnit>(loadUnit());

  @ViewChild('dial') dial?: ElementRef<SVGSVGElement>;

  unit: AngleUnit = AngleBlockUiComponent.unit$.getValue();
  // radians shown while the dial is dragged, committed on release
  preview: number | null = null;
  private readonly unitSub: Subscription;

  constructor(readonly cdr: ChangeDetectorRef) {
    super();
    this.unitSub = AngleBlockUiComponent.unit$.subscribe(u => {
      this.unit = u;
      this.cdr.markForCheck();
    });
  }

  ngOnDestroy(): void {
    this.unitSub.unsubscribe();
  }

  get fullTurn(): number | null {
    return this.resourceSchema?.angle_full_turn || null;
  }

  get radians(): number {
    if (this.preview !== null) return this.preview;
    const v = this.resourceData ?? 0;
    return this.fullTurn ? (v * TWO_PI) / this.fullTurn : v;
  }

  get displayValue(): number {
    const r = this.radians;
    return this.unit === 'deg' ? Math.round(((r * 180) / Math.PI) * 1000) / 1000 : Math.round(r * 1e5) / 1e5;
  }

  get step(): number {
    if (this.unit === 'rad') return 0.01;
    return 0.1;
  }

  get tooltip(): string {
    const raw =
      this.fullTurn && this.resourceData !== undefined
        ? `raw ${this.resourceData} (0x${this.resourceData.toString(16)})`
        : '';
    return [this.resourceDescription, raw].filter(x => x).join('\n\n');
  }

  // pointer of the dial: 0 to the right, growing clockwise
  get pointer(): { x: number; y: number } {
    return { x: 20 + 14 * Math.cos(this.radians), y: 20 + 14 * Math.sin(this.radians) };
  }

  // filled sector from 0 to the angle
  get sweepPath(): string {
    const a = this.radians % TWO_PI;
    if (a < 1e-6) return '';
    return `M20,20L38,20A18,18 0 ${a > Math.PI ? 1 : 0},1 ${20 + 18 * Math.cos(a)},${20 + 18 * Math.sin(a)}Z`;
  }

  toggleUnit() {
    const unit: AngleUnit = this.unit === 'deg' ? 'rad' : 'deg';
    try {
      localStorage.setItem(UNIT_STORAGE_KEY, unit);
    } catch {}
    AngleBlockUiComponent.unit$.next(unit);
  }

  onInput(raw: string) {
    const v = parseFloat(raw);
    if (!isFinite(v)) return;
    this.commit(this.unit === 'deg' ? (v * Math.PI) / 180 : v);
  }

  onDialDown(e: PointerEvent) {
    if (this.disabled || e.button !== 0) return;
    (e.target as Element).setPointerCapture?.(e.pointerId);
    this.onFocus();
    this.updatePreview(e);
  }

  onDialMove(e: PointerEvent) {
    if (this.preview !== null) this.updatePreview(e);
  }

  onDialUp() {
    if (this.preview === null) return;
    const value = this.preview;
    this.preview = null;
    this.onBlur();
    this.commit(value);
  }

  private updatePreview(e: PointerEvent) {
    const rect = this.dial!.nativeElement.getBoundingClientRect();
    let a = Math.atan2(e.clientY - rect.top - rect.height / 2, e.clientX - rect.left - rect.width / 2);
    if (a < 0) a += TWO_PI;
    if (e.shiftKey) a = ((Math.round((a * 180) / Math.PI / 15) * 15) % 360) * (Math.PI / 180);
    this.preview = a;
    this.cdr.markForCheck();
  }

  private commit(radians: number) {
    const value = this.fullTurn ? Math.round((radians * this.fullTurn) / TWO_PI) : radians;
    if (value !== this.resourceData) this.onValueSet(value);
    this.cdr.markForCheck();
  }
}
