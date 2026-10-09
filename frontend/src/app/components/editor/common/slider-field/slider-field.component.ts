import { ChangeDetectionStrategy, ChangeDetectorRef, Component, EventEmitter, Input, Output } from '@angular/core';
import { decimalsForStep, formatValue } from '../curve-editor/curve-editor.utils';

export type SliderSpec = {
  min: number;
  max: number;
  step: number;
  // shown value = value * scale (e.g. 100 for a fraction shown in %)
  scale?: number;
  unit?: string;
};

// A number with a slider over its usual range, for bounded values (factors, fractions). The number input still
// takes any value; the slider shows it clamped. Emits once per finished change (slider release or typed value)
@Component({
  selector: 'app-slider-field',
  templateUrl: './slider-field.component.html',
  styleUrls: ['./slider-field.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  standalone: false,
})
export class SliderFieldComponent {
  @Input() label = '';
  @Input() description = '';
  @Input() value: number | null | undefined = 0;
  @Input() spec: SliderSpec = { min: 0, max: 1, step: 0.01 };
  @Input() disabled: boolean | null | undefined = false;

  @Output() valueChange = new EventEmitter<number>();

  // shown value while the slider is dragged
  dragging: number | null = null;

  constructor(private readonly cdr: ChangeDetectorRef) {}

  get scale(): number {
    return this.spec.scale ?? 1;
  }

  get shown(): number {
    return this.dragging ?? (this.value ?? 0) * this.scale;
  }

  get decimals(): number {
    return decimalsForStep(this.spec.step * this.scale);
  }

  get displayValue(): string {
    return formatValue(this.shown, this.decimals);
  }

  get sliderValue(): number {
    return Math.max(this.spec.min * this.scale, Math.min(this.spec.max * this.scale, this.shown));
  }

  onSlide(raw: string) {
    this.dragging = parseFloat(raw);
    this.cdr.markForCheck();
  }

  onSlideEnd(raw: string) {
    this.dragging = null;
    this.emit(parseFloat(raw));
  }

  onTyped(raw: string) {
    this.emit(parseFloat(raw));
  }

  private emit(shown: number) {
    if (!isFinite(shown)) return;
    const value = shown / this.scale;
    if (value !== this.value) this.valueChange.emit(value);
    this.cdr.markForCheck();
  }
}
