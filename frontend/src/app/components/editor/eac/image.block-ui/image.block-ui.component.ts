import { AfterViewInit, ChangeDetectionStrategy, Component, ElementRef, inject, ViewChild } from '@angular/core';
import { SubscribableGuiComponent } from '../../gui.component';
import { filter, Subject, takeUntil } from 'rxjs';
import { BlockData, BlockSchema, CustomAction } from '../../types';
import { CustomActionService } from '../../../../services/custom-action.service';
import { MatSelectChange } from '@angular/material/select';
import { ImageViewerComponent } from '../../common/image-viewer/image-viewer.component';
import { joinId } from '../../../../utils/join-id';
import { ChangeEntry } from '../../../../services/changes.service';

// The extra embedded palette fields on `EacImage`, treated in the GUI as a max-3-length array.
const EMBEDDED_PALETTE_EXTRA_FIELDS = ['embedded_palette_2', 'embedded_palette_3', 'embedded_palette_4'];

const isPowerOfTwo = (n: number | undefined): boolean => !!n && n > 0 && (n & (n - 1)) === 0;

@Component({
  selector: 'image-block-ui',
  templateUrl: './image.block-ui.component.html',
  styleUrls: ['./image.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  standalone: false,
})
export class ImageBlockUiComponent extends SubscribableGuiComponent implements AfterViewInit {
  private readonly destroyed$: Subject<void> = new Subject<void>();

  @ViewChild('viewer') viewer?: ImageViewerComponent;

  readonly customActionService = inject(CustomActionService);
  protected readonly joinId = joinId;

  async ngAfterViewInit() {
    this.changes.change$
      .pipe(
        takeUntil(this.destroyed$),
        filter(x => x.includes('colors/data')),
      )
      .subscribe(() => {
        if (this.viewer) {
          this.viewer.imageNeedsUpdate$.next();
        }
      });
  }

  override ngOnDestroy(): void {
    super.ngOnDestroy();
    this.destroyed$.next();
    this.destroyed$.complete();
  }

  async onFormatChange(event: MatSelectChange) {
    const newFormat = event.value;
    if (!this._resourceData || this._resourceData.resource_id === newFormat) return;

    const customActionSimplifiedFormat = (resourceId: string): 'rgba' | '4bit' | '8bit' => {
      if (resourceId.startsWith('4Bit')) {
        return '4bit';
      } else if (resourceId === '8Bit') {
        return '8bit';
      } else {
        return 'rgba';
      }
    };
    const currentFormatSmpl = customActionSimplifiedFormat(this._resourceData.resource_id);
    const newFormatSmpl = customActionSimplifiedFormat(newFormat);

    const action = this.resourceSchema.custom_actions.find(
      (a: CustomAction) => a.method === 'convert_to_' + newFormatSmpl,
    )!;
    const formPatch: any = {};
    if (newFormatSmpl === 'rgba') {
      if (currentFormatSmpl === 'rgba') {
        formPatch['output_colors'] = 'use palette'; // this variable is unused when converting rgba -> rgba
      }
      formPatch['color_mode'] = newFormat;
    }
    if (newFormatSmpl === '8bit' && currentFormatSmpl === '4bit') {
      formPatch['channel'] = ''; // both variables are unused when converting 4bit -> 8bit
      formPatch['palette_type'] = '';
    }
    if (newFormatSmpl === '4bit') {
      formPatch['mode'] = newFormat;
      if (currentFormatSmpl === '8bit' || currentFormatSmpl === '4bit') {
        formPatch['channel'] = ''; // this variable is unused when converting 8bit -> 4bit
      }
    }
    const done = await this.customActionService.runCustomAction(this.resourceId!, action, formPatch, true);
    if (!done) {
      // restore value in the input
      event.source.value = this.resourceData.resource_id;
    }
  }

  // Fields rendered by bespoke UI below rather than by the generic compound field list.
  private static readonly BASE_FIELD_BLACKLIST = ['resource_id', ...EMBEDDED_PALETTE_EXTRA_FIELDS, 'mipmaps'];
  private static readonly NON_8BIT_FIELD_BLACKLIST = [
    ...ImageBlockUiComponent.BASE_FIELD_BLACKLIST,
    'embedded_palette',
  ];

  get fieldBlacklist(): string[] {
    // embedded_palette only applies to 8Bit bitmaps - hide it entirely otherwise.
    return this.resourceData?.resource_id === '8Bit'
      ? ImageBlockUiComponent.BASE_FIELD_BLACKLIST
      : ImageBlockUiComponent.NON_8BIT_FIELD_BLACKLIST;
  }

  // Unchecking clears `mipmaps` generically; checking runs `generate_mipmaps` so the backend
  // computes the mip chain from the current bitmap.
  get mipmapsPresent(): boolean {
    return this.resourceData?.mipmaps !== null && this.resourceData?.mipmaps !== undefined;
  }

  get mipmapsAllowed(): boolean {
    let d = this.resourceData;
    if (!d) return false;
    return d.width > 1 && d.height > 1 && isPowerOfTwo(d.width) && isPowerOfTwo(d.height);
  }

  async onMipmapsToggle(checked: boolean): Promise<void> {
    if (!this.resourceId || checked === this.mipmapsPresent) return;
    if (!checked) {
      this.onValueSet(null, 'mipmaps');
      return;
    }
    const action = this.resourceSchema?.custom_actions?.find((a: CustomAction) => a.method === 'generate_mipmaps');
    if (!action) return;
    await this.customActionService.runCustomAction(this.resourceId, action, {}, true);
    this.cdr.markForCheck();
  }

  // The format writes the first palette it finds into `embedded_palette`, so the extra ones can
  // never be populated while it's absent.
  get showEmbeddedPalettesArray(): boolean {
    return this.resourceData?.resource_id === '8Bit' && !!this.resourceData?.embedded_palette;
  }

  get embeddedPaletteSlots(): (BlockData | null)[] {
    return EMBEDDED_PALETTE_EXTRA_FIELDS.map(field => this.resourceData?.[field] ?? null);
  }

  get embeddedPaletteCount(): number {
    return this.embeddedPaletteSlots.filter(v => v !== null).length;
  }

  get embeddedPaletteChildSchema(): BlockSchema | undefined {
    return this.resourceSchema?.fields?.find((f: any) => f.name === EMBEDDED_PALETTE_EXTRA_FIELDS[0])?.schema
      ?.child_schema;
  }

  embeddedPaletteFieldId(index: number): string {
    return joinId(this.resourceId!, EMBEDDED_PALETTE_EXTRA_FIELDS[index]);
  }

  async addEmbeddedPalette(): Promise<void> {
    const count = this.embeddedPaletteCount;
    if (!this.resourceId || count >= EMBEDDED_PALETTE_EXTRA_FIELDS.length) return;
    const fieldId = this.embeddedPaletteFieldId(count);
    const newValue = await this.mainService.getTrailingOptionalFieldData(fieldId);
    if (newValue === null || newValue === undefined) return;
    this.onValueSet(newValue, EMBEDDED_PALETTE_EXTRA_FIELDS[count]);
  }

  removeEmbeddedPalette(index: number): void {
    const slots = this.embeddedPaletteSlots;
    slots.splice(index, 1);
    slots.push(null);
    this.applyEmbeddedPaletteSlots(slots);
  }

  moveEmbeddedPaletteUp(index: number): void {
    if (index <= 0) return;
    this.swapEmbeddedPalettes(index, index - 1);
  }

  moveEmbeddedPaletteDown(index: number): void {
    if (index >= this.embeddedPaletteCount - 1) return;
    this.swapEmbeddedPalettes(index, index + 1);
  }

  private swapEmbeddedPalettes(indexA: number, indexB: number): void {
    const slots = this.embeddedPaletteSlots;
    [slots[indexA], slots[indexB]] = [slots[indexB], slots[indexA]];
    this.applyEmbeddedPaletteSlots(slots);
  }

  // Replaces all 3 slots as a single undoable bundle.
  private applyEmbeddedPaletteSlots(newSlots: (BlockData | null)[]): void {
    if (!this.resourceId) return;
    const oldSlots = this.embeddedPaletteSlots;
    const changes: ChangeEntry[] = [];
    EMBEDDED_PALETTE_EXTRA_FIELDS.forEach((field, i) => {
      const oldValue = oldSlots[i] ?? null;
      const newValue = newSlots[i] ?? null;
      if (oldValue !== newValue) {
        changes.push({
          op: 'set',
          id: joinId(this.resourceId!, field),
          timestamp: Date.now(),
          oldValue,
          newValue,
        });
      }
    });
    if (changes.length > 0) {
      this.emitNewChange({ op: 'bundle', changes });
    }
  }
}
