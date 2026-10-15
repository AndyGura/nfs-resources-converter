import { AfterViewInit, ChangeDetectionStrategy, Component, ElementRef, inject, ViewChild } from '@angular/core';
import { SubscribableGuiComponent } from '../../gui.component';
import { filter, Subject, takeUntil } from 'rxjs';
import { BlockData, BlockSchema, CustomAction } from '../../types';
import { CustomActionService } from '../../../../services/custom-action.service';
import { MatSelectChange } from '@angular/material/select';
import {
  ImageMarker,
  ImageMarkerMove,
  ImageOverlay,
  ImageViewerComponent,
} from '../../common/image-viewer/image-viewer.component';
import { joinId } from '../../../../utils/join-id';
import { ChangeEntry } from '../../../../services/changes.service';
import { MatDialog } from '@angular/material/dialog';
import { firstValueFrom } from 'rxjs';
import { ConfirmDialogComponent } from '../../../confirm.dialog/confirm.dialog.component';

type SiblingStats = { images: number; color_models: { [model: string]: number }; with_mipmaps: number };

// the color models of `EacImage.resource_id`, grouped for the select
const COLOR_MODEL_GROUPS: { name: string; models: string[] }[] = [
  { name: 'Palette', models: ['8Bit', '4Bit', '4Bit (swapped)', '4Bit PS1'] },
  {
    name: 'Direct color',
    models: [
      '16Bit_0565 color format bitmap',
      '16Bit_1555 color format bitmap',
      '16Bit_4444 color format bitmap',
      '24Bit color format bitmap',
      '32Bit color format bitmap',
    ],
  },
  { name: 'Compressed', models: ['DXT1 compressed bitmap', 'DXT3 compressed bitmap', 'DXT5 compressed bitmap'] },
];

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
  private readonly dialog = inject(MatDialog);
  protected readonly joinId = joinId;

  // every model of the enum, in groups (a model missing from the groups goes to the last one)
  get colorModelGroups(): { name: string; models: string[] }[] {
    const all: string[] = (this.resourceSchema?.fields?.[0]?.schema?.enum_names || []).map((x: any) => x[1]);
    const grouped = COLOR_MODEL_GROUPS.flatMap(g => g.models);
    const groups = COLOR_MODEL_GROUPS.map(g => ({ ...g, models: g.models.filter(m => all.includes(m)) }));
    groups[groups.length - 1].models.push(...all.filter(m => !grouped.includes(m)));
    return groups.filter(g => g.models.length > 0);
  }

  siblingStats: SiblingStats | null = null;
  private siblingStatsId: string | null = null;

  // what the other images of the SHPI use: loaded on demand (it parses every entry of the SHPI)
  async loadSiblingStats(): Promise<SiblingStats | null> {
    if (!this.resourceId) return null;
    if (this.siblingStatsId !== this.resourceId) {
      this.siblingStatsId = this.resourceId;
      this.siblingStats = null;
      try {
        this.siblingStats = await this.mainService.api.archiveImageStats(this.resourceId);
      } catch {
        this.siblingStatsId = null;
      }
      this.cdr.markForCheck();
    }
    return this.siblingStats;
  }

  private async confirm(text: string): Promise<boolean> {
    return !!(await firstValueFrom(this.dialog.open(ConfirmDialogComponent, { data: { text } }).afterClosed()));
  }

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
    this.changes.change$
      .pipe(
        takeUntil(this.destroyed$),
        filter(
          x =>
            !!this.resourceId &&
            (x.startsWith(joinId(this.resourceId, 'hot_spots')) || x.startsWith(joinId(this.resourceId, 'pivot'))),
        ),
      )
      .subscribe(() => this.cdr.markForCheck());
  }

  override ngOnDestroy(): void {
    super.ngOnDestroy();
    this.destroyed$.next();
    this.destroyed$.complete();
  }

  async onFormatChange(event: MatSelectChange) {
    const newFormat = event.value;
    if (!this._resourceData || this._resourceData.resource_id === newFormat) return;
    const stats = await this.loadSiblingStats();
    if (stats && stats.images > 0 && !stats.color_models[newFormat]) {
      const used = Object.keys(stats.color_models).join(', ');
      const go = await this.confirm(
        `No other image of this SHPI is ${newFormat} (they are ${used}). The game may not read it. Convert anyway?`,
      );
      if (!go) {
        event.source.value = this.resourceData.resource_id;
        return;
      }
    }

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
    // Only 8Bit bitmaps need an embedded palette, but other ones can have one too (NFS6 4Bit fonts): offer it on
    // 8Bit bitmaps, show it on the others when they have it.
    return this.resourceData?.resource_id === '8Bit' || !!this.resourceData?.embedded_palette
      ? ImageBlockUiComponent.BASE_FIELD_BLACKLIST
      : ImageBlockUiComponent.NON_8BIT_FIELD_BLACKLIST;
  }

  private hotSpotOverlaysKey = '';
  private hotSpotOverlaysCache: ImageOverlay[] = [];

  // the same array while the inputs are the same: a new one on every check would be a changed binding
  get hotSpotOverlays(): ImageOverlay[] {
    const data = this.resourceData;
    const points = data?.hot_spots?.points;
    const key = JSON.stringify([points, data?.pivot, data?.width, data?.height, this.resourceId, this.resourceName]);
    if (key !== this.hotSpotOverlaysKey) {
      this.hotSpotOverlaysKey = key;
      const markers = points ? this.buildHotSpotMarkers(data!) : [];
      this.hotSpotOverlaysCache =
        markers.length > 0 ? [{ name: 'Hot spots', icon: 'my_location', markers, editable: true }] : [];
      if (this.isTnfsHorizon && data) {
        // ring type 0 scrolls the horizon with this row on the horizon line (see `pivot`)
        this.hotSpotOverlaysCache.push({
          name: 'Horizon line',
          icon: 'horizontal_rule',
          markers: [],
          lines: [{ y: data.pivot?.y ?? 0, label: `horizon (pivot.y ${data.pivot?.y ?? 0})` }],
        });
      }
    }
    return this.hotSpotOverlaysCache;
  }

  // the horizon bitmap of a TNFS track (FAM)
  private get isTnfsHorizon(): boolean {
    return this.resourceName === 'horz' && !!this.resourceId && this.resourceId.toUpperCase().includes('.FAM__');
  }

  // a dropped marker: the point is relative to the bitmap moved by `pivot`, one undoable change for x and y
  onHotSpotMoved(move: ImageMarkerMove) {
    const data = this.resourceData;
    if (move.overlay !== 'Hot spots' || !this.resourceId || !data?.hot_spots) return;
    const index = +this.hotSpotOverlaysCache[0].markers[move.index].label;
    const point = data.hot_spots.points[index];
    const pivot = data.pivot ?? { x: 0, y: 0 };
    const x = move.x - pivot.x;
    const y = move.y - pivot.y;
    const changes: ChangeEntry[] = [];
    for (const [axis, value] of [
      ['x', x],
      ['y', y],
    ] as const) {
      if (point[axis] !== value) {
        changes.push({
          op: 'set',
          id: joinId(this.resourceId, 'hot_spots', 'points', index, axis),
          timestamp: Date.now(),
          oldValue: point[axis],
          newValue: value,
        });
      }
    }
    if (changes.length > 0) {
      this.emitNewChange({ op: 'bundle', changes });
    }
  }

  // Hot spot points are relative to the bitmap moved by `pivot` (TNFS dashboards draw them at position + pivot +
  // point), the ones out of the bitmap are left out (1x1 placeholder bitmaps carry the points of another bitmap)
  private buildHotSpotMarkers(data: BlockData): ImageMarker[] {
    const pivot = data.pivot ?? { x: 0, y: 0 };
    return data.hot_spots.points
      .map((p: { x: number; y: number }, i: number) => ({
        x: pivot.x + p.x,
        y: pivot.y + p.y,
        label: '' + i,
        title: `Hot spot #${i}: (${p.x}, ${p.y})`,
      }))
      .filter((m: ImageMarker) => m.x >= 0 && m.y >= 0 && m.x < data.width && m.y < data.height);
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

  async onMipmapsToggle(checked: boolean, checkbox?: { checked: boolean }): Promise<void> {
    if (!this.resourceId || checked === this.mipmapsPresent) return;
    if (!checked) {
      this.onValueSet(null, 'mipmaps');
      return;
    }
    const stats = await this.loadSiblingStats();
    if (!stats?.with_mipmaps) {
      const d = this.resourceData!;
      let levels = 0;
      for (let w = d.width, h = d.height; w > 1 || h > 1; w = Math.max(1, w >> 1), h = Math.max(1, h >> 1)) levels++;
      const y = d.position?.y ?? 0;
      const newY = (y & 0xfff) | (levels << 12);
      const go = await this.confirm(
        `No other image of this SHPI has mipmaps: only NFS5 reads them. Their level count is stored in the 4 high ` +
          `bits of position.y (${y} becomes ${newY}), which menus and dashboards use to place the image. ` +
          `Generate mipmaps anyway?`,
      );
      if (!go) {
        if (checkbox) checkbox.checked = false;
        return;
      }
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
