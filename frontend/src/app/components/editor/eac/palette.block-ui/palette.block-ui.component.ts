import { AfterViewInit, ChangeDetectionStrategy, Component, ElementRef, inject, ViewChild } from '@angular/core';
import { SubscribableGuiComponent } from '../../gui.component';
import { joinId } from '../../../../utils/join-id';
import { MatSelectChange } from '@angular/material/select';
import { CustomAction } from '../../types';
import { CustomActionService } from '../../../../services/custom-action.service';
import { parseColorInputValue } from '../../../../utils/parse-color-input-value';
import { auditTime, Subject, takeUntil } from 'rxjs';
import { ChangeEntry } from '../../../../services/changes.service';

// TNFS car textures (CFM): entries the game recolors (`serializers/misc/tnfs_car_colors.py`)
const TNFS_CAR_SPECIAL_ENTRIES: { [index: number]: string } = {
  250: 'light bar (cop siren)',
  251: 'light bar (cop siren)',
  252: 'light bar (cop siren)',
  253: 'light bar (cop siren)',
  254: 'tail lights',
  255: 'transparent',
};

// internal color (0xRRGGBBAA) with the hue turned by `degrees`
function shiftHue(color: number, degrees: number): number {
  const r = ((color >>> 24) & 0xff) / 255;
  const g = ((color >>> 16) & 0xff) / 255;
  const b = ((color >>> 8) & 0xff) / 255;
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const l = (max + min) / 2;
  const d = max - min;
  if (d === 0) return color >>> 0;
  const s = d / (1 - Math.abs(2 * l - 1));
  let h = max === r ? ((g - b) / d) % 6 : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
  h = (((h * 60 + degrees) % 360) + 360) % 360;
  const c = (1 - Math.abs(2 * l - 1)) * s;
  const x = c * (1 - Math.abs(((h / 60) % 2) - 1));
  const m = l - c / 2;
  const [r1, g1, b1] =
    h < 60
      ? [c, x, 0]
      : h < 120
        ? [x, c, 0]
        : h < 180
          ? [0, c, x]
          : h < 240
            ? [0, x, c]
            : h < 300
              ? [x, 0, c]
              : [c, 0, x];
  const to = (v: number) => Math.round((v + m) * 255);
  return ((to(r1) << 24) | (to(g1) << 16) | (to(b1) << 8) | (color & 0xff)) >>> 0;
}

@Component({
  selector: 'app-palette-block-ui',
  templateUrl: './palette.block-ui.component.html',
  styleUrls: ['./palette.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  standalone: false,
})
export class PaletteBlockUiComponent extends SubscribableGuiComponent implements AfterViewInit {
  @ViewChild('colorInput') colorInput!: ElementRef<HTMLInputElement>;

  readonly customActionService = inject(CustomActionService);

  override get resourceId(): string | undefined {
    return super.resourceId;
  }

  override set resourceId(value: string | undefined) {
    const changed = value !== super.resourceId;
    super.resourceId = value;
    if (changed) {
      this.selection.clear();
      this.usedIndices = null;
      this.loadUsage();
    }
  }

  // indices the images using this palette hold (null until known)
  usedIndices: Set<number> | null = null;
  selection = new Set<number>();
  private anchor: number | null = null;
  private pickForSelection = false;
  hueShift = 0;

  private async loadUsage() {
    const id = this.resourceId;
    if (!id) return;
    try {
      const used = await this.mainService.api.paletteUsage(id);
      if (this.resourceId === id) {
        this.usedIndices = new Set(used);
        this.cdr.markForCheck();
      }
    } catch {}
  }

  specialLabel(index: number): string | null {
    return this.resourceId?.toUpperCase().includes('.CFM__') ? (TNFS_CAR_SPECIAL_ENTRIES[index] ?? null) : null;
  }

  colorTooltip(index: number, color: number): string {
    let text = index + ': #' + this.lpad(color.toString(16), '0', 8);
    const special = this.specialLabel(index);
    if (special) text += ' — ' + special;
    if (this.usedIndices && !this.usedIndices.has(index)) text += ' — not used by the images';
    return text;
  }

  clearSelection() {
    this.selection.clear();
    this.anchor = null;
    this.cdr.markForCheck();
  }

  // one undoable change for every selected color
  private setColors(newColors: Map<number, number>) {
    const colors = this.resourceData?.colors.data;
    if (!this.resourceId || !colors) return;
    const changes: ChangeEntry[] = [];
    for (const [index, value] of newColors) {
      if (colors[index] !== value) {
        changes.push({
          op: 'set',
          id: joinId(this.resourceId, 'colors', 'data', index),
          timestamp: Date.now(),
          oldValue: colors[index],
          newValue: value,
        });
      }
    }
    if (changes.length > 0) {
      this.emitNewChange({ op: 'bundle', changes });
    }
  }

  pickSelectionColor() {
    this.pickForSelection = true;
    const first = Math.min(...this.selection);
    this.colorInput.nativeElement.value = '#' + this.lpad(this.resourceData!.colors.data[first].toString(16), '0', 8);
    this.colorInput.nativeElement.click();
  }

  shiftSelectionHue() {
    const colors: number[] = this.resourceData?.colors.data || [];
    this.setColors(new Map([...this.selection].map(i => [i, shiftHue(colors[i], +this.hueShift)])));
  }
  valueChange$: Subject<[number, number]> = new Subject<[number, number]>();
  destroyed$: Subject<void> = new Subject<void>();

  ngAfterViewInit(): void {
    this.valueChange$.pipe(takeUntil(this.destroyed$), auditTime(150)).subscribe(([index, value]) => {
      this.onValueSet(value, 'colors', 'data', index);
    });
  }

  override ngOnDestroy() {
    super.ngOnDestroy();
    this.destroyed$.next();
    this.destroyed$.complete();
    this.valueChange$.complete();
  }

  lpad(str: string, padString: string, length: number) {
    while (str.length < length) str = padString + str;
    return str;
  }

  getColorGradient(color: number) {
    const hex = this.lpad(color.toString(16), '0', 8);
    const solid = '#' + hex.substring(0, 6);
    const full = '#' + hex;
    return `linear-gradient(135deg, ${solid} 50%, ${full} 50%)`;
  }

  private selectedIndex: number | null = null;

  onColorClicked(em: HTMLDivElement, index: number, event?: MouseEvent) {
    if (!this.resourceData) {
      this.selectedIndex = null;
      return;
    }
    if (event?.shiftKey && this.anchor !== null) {
      for (let i = Math.min(this.anchor, index); i <= Math.max(this.anchor, index); i++) this.selection.add(i);
      this.cdr.markForCheck();
      return;
    }
    if (event?.ctrlKey || event?.metaKey || event?.shiftKey) {
      if (!this.selection.delete(index)) this.selection.add(index);
      this.anchor = index;
      this.cdr.markForCheck();
      return;
    }
    this.selection.clear();
    this.anchor = index;
    this.pickForSelection = false;
    this.selectedIndex = index;
    this.colorInput.nativeElement.value =
      '#' + this.lpad(this.resourceData.colors.data[this.selectedIndex].toString(16), '0', 8);

    const rect = em.getBoundingClientRect();
    this.colorInput.nativeElement.style.left = `${rect.left}px`;
    this.colorInput.nativeElement.style.top = `${rect.top}px`;
    this.colorInput.nativeElement.style.width = `${rect.width}px`;
    this.colorInput.nativeElement.style.height = `${rect.height}px`;

    this.colorInput.nativeElement.click();
  }

  onColorChange(raw: string | null) {
    if (this.pickForSelection) {
      this.pickForSelection = false;
      const colors: number[] = this.resourceData?.colors.data || [];
      const updates = new Map<number, number>();
      for (const i of this.selection) {
        const value = parseColorInputValue(raw, colors[i] & 0xff);
        if (value !== null) updates.set(i, value);
      }
      this.setColors(updates);
      return;
    }
    if (!this.resourceId || !this.resourceData || this.selectedIndex === null) {
      this.selectedIndex = null;
      return;
    }
    const color = this.resourceData.colors.data[this.selectedIndex];
    const alpha = color & 0xff;
    const value = parseColorInputValue(raw, alpha);
    if (value === null) return;
    this.valueChange$.next([this.selectedIndex, value]);
  }

  async addColor() {
    if (!this.resourceId || !this.resourceData) return;
    this.emitNewChange({
      id: joinId(this.resourceId!, 'colors', 'data'),
      op: 'array_insert',
      index: this.resourceData.colors.data.length,
      value: 0xff,
    });
  }

  removeLastColor() {
    if (!this.resourceId || !this.resourceData || this.resourceData.colors.data.length === 0) return;
    this.emitNewChange({
      id: joinId(this.resourceId!, 'colors', 'data'),
      op: 'array_remove',
      index: this.resourceData.colors.data.length - 1,
      oldValue: this.resourceData.colors.data[this.resourceData.colors.data.length - 1],
    });
  }

  async onFormatChange(event: MatSelectChange) {
    const newFormat = event.value;
    if (!this._resourceData || this._resourceData.resource_id === newFormat) return;
    const action = this.resourceSchema.custom_actions.find((a: CustomAction) => a.method === 'convert_format')!;
    const formPatch: any = { color_mode: newFormat };
    const done = await this.customActionService.runCustomAction(this.resourceId!, action, formPatch, true);
    if (!done) {
      // restore value in the input
      event.source.value = this.resourceData.resource_id;
    }
  }
}
