import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  inject,
  NgZone,
  ViewChild,
} from '@angular/core';
import { auditTime, BehaviorSubject, combineLatest, filter, startWith, Subject, takeUntil } from 'rxjs';
import { BlockData, BlockSchema } from '../../types';
import { ArrayTableColumn, DataTableComponent } from '../../common/data-table/data-table.component';
import { joinId } from '../../../../utils/join-id';
import { SubscribableGuiComponent } from '../../gui.component';
import { ChangeEntry } from '../../../../services/changes.service';
import { numberRange } from '../../value-validators';

// index of an item with `key` = `value` in `items` without the item at `excludeIndex`: after all items with a key
// <= value, so a sorted array stays sorted and equal keys keep their order
export function sortedPosition(items: any[], key: string, value: number, excludeIndex: number): number {
  let position = 0;
  items.forEach((item, i) => {
    if (i !== excludeIndex && item[key] <= value) position++;
  });
  return position;
}

@Component({
  selector: 'app-font-block-ui',
  templateUrl: './font.block-ui.component.html',
  styleUrls: ['./font.block-ui.component.scss'],
  host: { class: 'full-screen-editor' },
  changeDetection: ChangeDetectionStrategy.Eager,
  standalone: false,
})
export class FontBlockUiComponent extends SubscribableGuiComponent implements AfterViewInit {
  @ViewChild('fullBitmapCanvas') fullBitmapCanvas?: ElementRef<HTMLCanvasElement>;
  @ViewChild('textPreviewCanvas') textPreviewCanvas!: ElementRef<HTMLCanvasElement>;
  @ViewChild('glyphsTable') glyphsTable?: DataTableComponent;
  @ViewChild('kerningsTable') kerningsTable?: DataTableComponent;

  _selectedGlyphIndex$: BehaviorSubject<number | null> = new BehaviorSubject<number | null>(0);
  _selectedKerningIndex$: BehaviorSubject<number | null> = new BehaviorSubject<number | null>(0);
  _selectedTabIndex: number = 0;
  set selectedTabIndex(value: number) {
    this._selectedTabIndex = value;
    this._selectedTabIndex$.next(value);
  }

  get selectedTabIndex(): number {
    return this._selectedTabIndex;
  }

  get isCharPreviewVisible(): boolean {
    return this.selectedTabIndex === 0;
  }

  static readonly SAMPLE_TEXT =
    'The quick brown fox jumps over the lazy dog\n0123456789\n!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~';
  _text$: BehaviorSubject<string> = new BehaviorSubject<string>(FontBlockUiComponent.SAMPLE_TEXT);

  _glyphColumns: ArrayTableColumn[] = [];
  _kerningColumns: ArrayTableColumn[] = [];

  public _glyphsWithSymbols$ = new BehaviorSubject<any[]>([]);
  public _kerningsWithSymbols$ = new BehaviorSubject<any[]>([]);
  public _glyphPageSize = 100;
  public _glyphPageIndex = 0;
  public _kerningPageSize = 100;
  public _kerningPageIndex = 0;
  private _hideHiddenFields = true;
  // order problems of data opened that way (imported fonts): the writer sorts on save, "Sort now" does it here
  public _glyphsUnsorted = false;
  public _duplicateGlyphCodes: number[] = [];
  public _kerningsUnsorted = false;

  // glyphs are sorted by code. Kernings of versions > 309 are sorted by right glyph: a glyph's num_kern and
  // kern_index point at a run of them
  get kerningsSortField(): string | null {
    return this.resourceData?.version > 309 ? 'right' : null;
  }

  override get resourceSchema(): BlockSchema | undefined {
    return super.resourceSchema;
  }

  override set resourceSchema(value: BlockSchema | undefined) {
    super.resourceSchema = value;
    this.updateColumns();
    this.refreshImage().then();
  }

  override get resourceData(): BlockData | undefined {
    return super.resourceData;
  }

  override set resourceData(value: BlockData | undefined) {
    super.resourceData = value;
    this.updateColumns();
    this.refreshImage().then();
    this.updateSymbols();
  }

  private updateSymbols() {
    if (!this.resourceData) {
      this._glyphsWithSymbols$.next([]);
      this._kerningsWithSymbols$.next([]);
      return;
    }
    // num_kern and kern_index are recomputed on save, with kernings sorted by right glyph: show the values the file
    // will get
    const kerningRuns = new Map<number, { first: number; count: number }>();
    for (const k of this.resourceData.kernings || []) {
      const run = kerningRuns.get(k.right);
      if (run) run.count++;
      else kerningRuns.set(k.right, { first: 0, count: 1 });
    }
    let first = 0;
    for (const right of Array.from(kerningRuns.keys()).sort((a, b) => a - b)) {
      kerningRuns.get(right)!.first = first;
      first += kerningRuns.get(right)!.count;
    }
    const definitions = this.resourceData.definitions;
    this._glyphsUnsorted = definitions.some((g: any, i: number) => i > 0 && definitions[i - 1].code > g.code);
    const seenCodes = new Set<number>();
    const duplicateCodes = new Set<number>();
    for (const g of definitions) {
      if (seenCodes.has(g.code)) duplicateCodes.add(g.code);
      seenCodes.add(g.code);
    }
    this._duplicateGlyphCodes = Array.from(duplicateCodes);
    const kerningsList = this.resourceData.kernings || [];
    this._kerningsUnsorted =
      !!this.kerningsSortField &&
      kerningsList.some((k: any, i: number) => i > 0 && kerningsList[i - 1].right > k.right);
    const glyphs = definitions.map((g: any) => {
      const run = kerningRuns.get(g.code);
      const row = { ...g, symbol: this.getSymbol(g.code) };
      if (g.num_kern != null) row.num_kern = run?.count || 0;
      if (g.kern_index != null) row.kern_index = run?.first || 0;
      return row;
    });
    this._glyphsWithSymbols$.next(glyphs);

    const kernings = (this.resourceData.kernings || []).map((k: any) => ({
      ...k,
      'Left Symbol': this.getSymbol(k.left),
      'Right Symbol': this.getSymbol(k.right),
      'Left Symbol Code': k.left,
      'Right Symbol Code': k.right,
      Kerning: k.kerning,
      Unk: k.unk,
    }));
    this._kerningsWithSymbols$.next(kernings);
  }

  private readonly destroyed$: Subject<void> = new Subject<void>();
  private _selectedTabIndex$ = new BehaviorSubject<number>(0);
  private _image: HTMLImageElement | null = null;
  private _imageRefreshed$: Subject<void> = new Subject<void>();
  private _resizeObserver: ResizeObserver | null = null;
  private _resized$: Subject<void> = new Subject<void>();

  // Interactive view state
  private _hasCustomView: boolean = false;
  private _viewRatio: number = 1;
  private _viewOffsetX: number = 0;
  private _viewOffsetY: number = 0;

  // Rectangle preview while dragging (in image coords)
  private _previewRect: { x: number; y: number; width: number; height: number } | null = null;
  private _previewOffset: { x: number; y: number } | null = null;
  private _previewAdvance: number | null = null;

  // Dragging state
  private _drag: {
    mode: 'move' | 'resize' | 'pan' | 'offset' | 'advance';
    edges?: { l?: boolean; r?: boolean; t?: boolean; b?: boolean };
    startMouseX: number;
    startMouseY: number;
    startRect: { x: number; y: number; width: number; height: number };
    startViewOffsetX?: number;
    startViewOffsetY?: number;
    startOffset?: { x: number; y: number };
    startAdvance?: number;
  } | null = null;

  private get currentGlyphIndex(): number | null {
    return this._selectedGlyphIndex$.getValue();
  }

  // the field holding a glyph's advance: 16-byte glyphs keep it in x_advance (advance is 0 in the game files)
  private get advanceKey(): 'advance' | 'x_advance' {
    return this.resourceData?.version >= 321 && this.resourceData?.flags?.format === '16-bytes'
      ? 'x_advance'
      : 'advance';
  }

  bitmapSchema() {
    return (this.resourceSchema.fields || []).find((x: { name: string; schema: BlockSchema }) => x.name === 'bitmap')
      ?.schema;
  }

  readonly ngZone = inject(NgZone);

  async ngAfterViewInit(): Promise<void> {
    this.mainService.hideHiddenFields$.pipe(takeUntil(this.destroyed$)).subscribe(hide => {
      this._hideHiddenFields = hide;
      this.updateColumns();
    });

    combineLatest([
      this._text$,
      this._imageRefreshed$,
      this._resized$,
      this.changes.change$.pipe(
        takeUntil(this.destroyed$),
        filter(x => !!this.resourceId && x.startsWith(this.resourceId)),
        startWith(null),
      ),
    ])
      .pipe(takeUntil(this.destroyed$), auditTime(50))
      .subscribe(([text]) => {
        this.ngZone.run(() => {
          this.renderTextPreview(text);
        });
      });

    combineLatest([
      this._selectedGlyphIndex$,
      this._imageRefreshed$,
      this._resized$,
      this.changes.change$.pipe(
        takeUntil(this.destroyed$),
        filter(x => !!this.resourceId && x.startsWith(this.resourceId)),
        startWith(null),
      ),
    ])
      .pipe(takeUntil(this.destroyed$), auditTime(50))
      .subscribe(([index]) => {
        this.ngZone.run(() => {
          this.renderFullBitmap(index);
        });
      });

    this.changes.change$
      .pipe(
        takeUntil(this.destroyed$),
        filter(x => !!this.resourceId && x.startsWith(this.resourceId)),
      )
      .subscribe(() => {
        this.updateSymbols();
      });

    this.changes.change$
      .pipe(
        takeUntil(this.destroyed$),
        filter(x => !!this.resourceId && x.startsWith(joinId(this.resourceId, `bitmap`))),
      )
      .subscribe(() => {
        this.refreshImage().then();
      });

    this._resizeObserver = new ResizeObserver(() => {
      this._resized$.next();
    });
    this._selectedTabIndex$.pipe(takeUntil(this.destroyed$)).subscribe(() => {
      if (this.fullBitmapCanvas) {
        this._resizeObserver?.observe(this.fullBitmapCanvas.nativeElement);
      }
      this._resized$.next();
    });
    // the panel, not the canvas: the canvas is as wide as its longest line
    this._resizeObserver.observe(this.textPreviewCanvas.nativeElement.parentElement!);

    this.changes.change$
      .pipe(
        takeUntil(this.destroyed$),
        filter(
          path =>
            !!this.resourceId &&
            (path === joinId(this.resourceId, 'version') || path.startsWith(joinId(this.resourceId, 'flags'))),
        ),
      )
      .subscribe(() => {
        this.updateColumns();
      });
  }

  private async refreshImage() {
    if (!this.resourceId) return;
    const paths = await this.mainService.api.serializeResource(this.resourceId);
    const imagePath = paths.find(x => x.endsWith('.png'));
    if (!imagePath) {
      this._image = null;
      return;
    }
    this._image = new Image();
    this._image.src = `${imagePath}?t=${new Date().getTime()}`;
    await new Promise(resolve => (this._image!.onload = resolve));
    this._imageRefreshed$.next();
  }

  private renderFullBitmap(index: number | null) {
    if (!this.resourceData || !this.fullBitmapCanvas) return;
    const canvas = this.fullBitmapCanvas.nativeElement;
    const ctx = canvas.getContext('2d');
    if (!ctx || !this._image) return;

    const imgWidth = this._image.width;
    const imgHeight = this._image.height;

    const canvasWidth = Math.floor(canvas.clientWidth || 420);
    const canvasHeight = Math.floor(canvas.clientHeight || 220);
    if (canvas.width !== canvasWidth || canvas.height !== canvasHeight) {
      canvas.width = canvasWidth;
      canvas.height = canvasHeight;
    }

    ctx.fillStyle = 'black';
    ctx.fillRect(0, 0, canvasWidth, canvasHeight);

    // Disable anti-aliasing (image smoothing)
    ctx.imageSmoothingEnabled = false;

    if (index === null) {
      // If no glyph selected, just draw the full image centered/fitted
      const scaleX = canvasWidth / imgWidth;
      const scaleY = canvasHeight / imgHeight;
      const ratio = Math.min(scaleX, scaleY);
      const offsetX = (canvasWidth - imgWidth * ratio) / 2;
      const offsetY = (canvasHeight - imgHeight * ratio) / 2;

      ctx.drawImage(this._image!, offsetX, offsetY, imgWidth * ratio, imgHeight * ratio);
      return;
    }

    const glyphs = this.resourceData.definitions;
    const glyph = glyphs[index];

    if (glyph) {
      // Calculate the bounding box that includes the glyph image, origin, and advance line
      const x_offset = glyph.x_offset || 0;
      const y_offset = glyph.y_offset || 0;
      const advance = glyph[this.advanceKey] || 0;

      // Origin point in image coordinates
      const originX = glyph.x - x_offset;
      const originY = glyph.y - y_offset;

      // The area we want to focus on (in image coordinates)
      const minX = Math.min(glyph.x, originX, originX + advance);
      const maxX = Math.max(glyph.x + glyph.width, originX, originX + advance);
      const minY = Math.min(glyph.y, originY);
      const maxY = Math.max(glyph.y + glyph.height, originY);

      const targetWidth = maxX - minX;
      const targetHeight = maxY - minY;

      // Scale to make this target area 50% of the canvas view
      const targetScale = 0.5;
      const scaleX = (canvasWidth * targetScale) / targetWidth;
      const scaleY = (canvasHeight * targetScale) / targetHeight;
      let ratio = Math.min(scaleX, scaleY);

      // Center the target area on the canvas
      let offsetX = canvasWidth / 2 - (minX + targetWidth / 2) * ratio;
      let offsetY = canvasHeight / 2 - (minY + targetHeight / 2) * ratio;

      // Ensure the target area doesn't overflow the view horizontally or vertically
      const areaCanvasX = offsetX + minX * ratio;
      const areaCanvasY = offsetY + minY * ratio;
      const areaCanvasW = targetWidth * ratio;
      const areaCanvasH = targetHeight * ratio;

      if (areaCanvasX < 0) offsetX -= areaCanvasX;
      else if (areaCanvasX + areaCanvasW > canvasWidth) offsetX -= areaCanvasX + areaCanvasW - canvasWidth;

      if (areaCanvasY < 0) offsetY -= areaCanvasY;
      else if (areaCanvasY + areaCanvasH > canvasHeight) offsetY -= areaCanvasY + areaCanvasH - canvasHeight;

      // Apply or capture custom view
      if (this._hasCustomView) {
        // Use stored view params
        ratio = this._viewRatio > 0 ? this._viewRatio : ratio;
        offsetX = this._viewOffsetX;
        offsetY = this._viewOffsetY;
      } else {
        // Initialize stored view from computed framing
        this._viewRatio = ratio;
        this._viewOffsetX = offsetX;
        this._viewOffsetY = offsetY;
      }

      // Draw full atlas image with current view
      ctx.drawImage(this._image!, offsetX, offsetY, imgWidth * ratio, imgHeight * ratio);

      // Pick rect to display: preview while dragging or current glyph
      const rectX = this._previewRect?.x ?? glyph.x;
      const rectY = this._previewRect?.y ?? glyph.y;
      const rectW = this._previewRect?.width ?? glyph.width;
      const rectH = this._previewRect?.height ?? glyph.height;

      const glyphCanvasX = offsetX + rectX * ratio;
      const glyphCanvasY = offsetY + rectY * ratio;
      const glyphCanvasW = rectW * ratio;
      const glyphCanvasH = rectH * ratio;

      // Draw bounding box
      ctx.strokeStyle = 'red';
      ctx.lineWidth = 2;
      ctx.strokeRect(glyphCanvasX, glyphCanvasY, glyphCanvasW, glyphCanvasH);

      // Draw resize handles if not zoomed out too much
      const handleSize = 6;
      const hs = handleSize;
      const drawHandle = (cx: number, cy: number) => {
        ctx.fillStyle = '#ff0000';
        ctx.fillRect(cx - hs / 2, cy - hs / 2, hs, hs);
        ctx.strokeStyle = '#000000';
        ctx.lineWidth = 1;
        ctx.strokeRect(cx - hs / 2, cy - hs / 2, hs, hs);
      };
      if (ratio >= 0.5) {
        // corners
        drawHandle(glyphCanvasX, glyphCanvasY);
        drawHandle(glyphCanvasX + glyphCanvasW, glyphCanvasY);
        drawHandle(glyphCanvasX, glyphCanvasY + glyphCanvasH);
        drawHandle(glyphCanvasX + glyphCanvasW, glyphCanvasY + glyphCanvasH);
        // edges midpoints
        drawHandle(glyphCanvasX + glyphCanvasW / 2, glyphCanvasY);
        drawHandle(glyphCanvasX + glyphCanvasW / 2, glyphCanvasY + glyphCanvasH);
        drawHandle(glyphCanvasX, glyphCanvasY + glyphCanvasH / 2);
        drawHandle(glyphCanvasX + glyphCanvasW, glyphCanvasY + glyphCanvasH / 2);
      }

      // Draw offset (x_offset, y_offset)
      const currentXOffset = this._previewOffset?.x ?? glyph.x_offset ?? 0;
      const currentYOffset = this._previewOffset?.y ?? glyph.y_offset ?? 0;

      const originCanvasX = offsetX + (rectX - currentXOffset) * ratio;
      const originCanvasY = offsetY + (rectY - currentYOffset) * ratio;

      // Draw origin point (Green circle)
      ctx.fillStyle = '#00ff00';
      ctx.beginPath();
      ctx.arc(originCanvasX, originCanvasY, 5, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = '#000000';
      ctx.lineWidth = 1;
      ctx.stroke();

      // Draw advance (Blue)
      const xAdvance = this._previewAdvance ?? glyph[this.advanceKey] ?? 0;
      ctx.strokeStyle = '#4040ff';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(originCanvasX, originCanvasY);
      ctx.lineTo(originCanvasX + xAdvance * ratio, originCanvasY);
      ctx.stroke();

      // Little tick at the end of advance
      const advanceEndX = originCanvasX + xAdvance * ratio;
      ctx.beginPath();
      ctx.moveTo(advanceEndX, originCanvasY - 8);
      ctx.lineTo(advanceEndX, originCanvasY + 8);
      ctx.stroke();

      // Draw handle at the end of advance
      ctx.fillStyle = '#4040ff';
      ctx.fillRect(advanceEndX - 3, originCanvasY - 8, 6, 16);
      ctx.strokeStyle = '#000000';
      ctx.lineWidth = 1;
      ctx.strokeRect(advanceEndX - 3, originCanvasY - 8, 6, 16);

      // the values the glyph has, or gets when the drag ends
      const readout =
        `x ${rectX}  y ${rectY}  w ${rectW}  h ${rectH}  ` +
        `offset ${currentXOffset}, ${currentYOffset}  advance ${xAdvance}`;
      ctx.font = '11px monospace';
      ctx.textBaseline = 'bottom';
      const readoutWidth = ctx.measureText(readout).width;
      ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
      ctx.fillRect(0, canvasHeight - 18, readoutWidth + 10, 18);
      ctx.fillStyle = this._drag ? '#ffeb3b' : '#e0e0e0';
      ctx.fillText(readout, 5, canvasHeight - 3);
    } else {
      // Default view if no glyph is selected
      const ratio = Math.min(canvasWidth / imgWidth, canvasHeight / imgHeight, 1.0);
      const drawWidth = imgWidth * ratio;
      const drawHeight = imgHeight * ratio;
      const offsetX = (canvasWidth - drawWidth) / 2;
      const offsetY = (canvasHeight - drawHeight) / 2;

      ctx.drawImage(this._image!, offsetX, offsetY, drawWidth, drawHeight);
    }
  }

  // ===== Mouse helpers and event handlers for Char Preview =====
  private getMouseCanvasPos(evt: MouseEvent, canvas: HTMLCanvasElement): { x: number; y: number } {
    const rect = canvas.getBoundingClientRect();
    return { x: evt.clientX - rect.left, y: evt.clientY - rect.top };
  }

  private canvasToImage(x: number, y: number): { x: number; y: number } {
    return { x: (x - this._viewOffsetX) / this._viewRatio, y: (y - this._viewOffsetY) / this._viewRatio };
  }

  private getCurrentRect(): { x: number; y: number; width: number; height: number } | null {
    const idx = this.currentGlyphIndex;
    if (idx === null) return null;
    const glyph: any = this.resourceData?.definitions?.[idx];
    if (!glyph) return null;
    if (this._previewRect) return this._previewRect;
    return { x: glyph.x, y: glyph.y, width: glyph.width, height: glyph.height };
  }

  private hitTest(
    canvasX: number,
    canvasY: number,
  ): {
    type: 'inside' | 'edge' | 'corner' | 'none' | 'offset' | 'advance';
    edges?: { l?: boolean; r?: boolean; t?: boolean; b?: boolean };
  } {
    const idx = this.currentGlyphIndex;
    if (idx === null) return { type: 'none' };
    const glyph: any = this.resourceData?.definitions?.[idx];
    const rect = this.getCurrentRect();
    const canvas = this.fullBitmapCanvas?.nativeElement;
    if (!rect || !canvas || !glyph) return { type: 'none' };
    const ratio = this._viewRatio;
    const offsetX = this._viewOffsetX;
    const offsetY = this._viewOffsetY;

    const x = offsetX + rect.x * ratio;
    const y = offsetY + rect.y * ratio;
    const w = rect.width * ratio;
    const h = rect.height * ratio;

    const currentXOffset = this._previewOffset?.x ?? glyph.x_offset ?? 0;
    const currentYOffset = this._previewOffset?.y ?? glyph.y_offset ?? 0;
    const originCanvasX = offsetX + (rect.x - currentXOffset) * ratio;
    const originCanvasY = offsetY + (rect.y - currentYOffset) * ratio;

    // Hit test for origin (offset) - green circle
    const distToOrigin = Math.sqrt(Math.pow(canvasX - originCanvasX, 2) + Math.pow(canvasY - originCanvasY, 2));
    if (distToOrigin <= 8) {
      return { type: 'offset' };
    }

    // Hit test for advance end
    const xAdvance = this._previewAdvance ?? glyph[this.advanceKey] ?? 0;
    const advanceEndX = originCanvasX + xAdvance * ratio;
    if (Math.abs(canvasX - advanceEndX) <= 8 && Math.abs(canvasY - originCanvasY) <= 12) {
      return { type: 'advance' };
    }

    // When zoomed out a lot, prioritize move over resize: disable handles below threshold
    const handleEnabled = ratio >= 0.5;
    const handleSize = 8;

    // Check handles first if enabled
    if (handleEnabled) {
      const within = (cx: number, cy: number) =>
        Math.abs(canvasX - cx) <= handleSize && Math.abs(canvasY - cy) <= handleSize;

      const centers = {
        tl: { x: x, y: y },
        tr: { x: x + w, y: y },
        bl: { x: x, y: y + h },
        br: { x: x + w, y: y + h },
        tm: { x: x + w / 2, y: y },
        bm: { x: x + w / 2, y: y + h },
        ml: { x: x, y: y + h / 2 },
        mr: { x: x + w, y: y + h / 2 },
      } as const;

      if (within(centers.tl.x, centers.tl.y)) return { type: 'corner', edges: { l: true, t: true } };
      if (within(centers.tr.x, centers.tr.y)) return { type: 'corner', edges: { r: true, t: true } };
      if (within(centers.bl.x, centers.bl.y)) return { type: 'corner', edges: { l: true, b: true } };
      if (within(centers.br.x, centers.br.y)) return { type: 'corner', edges: { r: true, b: true } };

      if (within(centers.tm.x, centers.tm.y)) return { type: 'edge', edges: { t: true } };
      if (within(centers.bm.x, centers.bm.y)) return { type: 'edge', edges: { b: true } };
      if (within(centers.ml.x, centers.ml.y)) return { type: 'edge', edges: { l: true } };
      if (within(centers.mr.x, centers.mr.y)) return { type: 'edge', edges: { r: true } };
    }

    // Inside rect check
    if (canvasX >= x && canvasX <= x + w && canvasY >= y && canvasY <= y + h) {
      return { type: 'inside' };
    }

    return { type: 'none' };
  }

  private setCursorForHit(hit: {
    type: 'inside' | 'edge' | 'corner' | 'none' | 'offset' | 'advance';
    edges?: { l?: boolean; r?: boolean; t?: boolean; b?: boolean };
  }) {
    const canvas = this.fullBitmapCanvas?.nativeElement;
    if (!canvas) return;
    let cursor = 'default';
    if (hit.type === 'inside') cursor = 'move';
    else if (hit.type === 'offset') cursor = 'move';
    else if (hit.type === 'advance') cursor = 'ew-resize';
    else if (hit.type === 'edge') {
      const e = hit.edges!;
      if (e.t || e.b) cursor = 'ns-resize';
      if (e.l || e.r) cursor = 'ew-resize';
    } else if (hit.type === 'corner') {
      const e = hit.edges!;
      if ((e.t && e.l) || (e.b && e.r)) cursor = 'nwse-resize';
      if ((e.t && e.r) || (e.b && e.l)) cursor = 'nesw-resize';
    } else if (hit.type === 'none') {
      cursor = 'grab';
    }
    canvas.style.cursor = cursor;
  }

  onFullCanvasMouseDown(evt: MouseEvent) {
    if (!this.resourceData || !this.fullBitmapCanvas) return;
    const canvas = this.fullBitmapCanvas.nativeElement;
    const pos = this.getMouseCanvasPos(evt, canvas);

    const hit = this.hitTest(pos.x, pos.y);

    const rect = this.getCurrentRect();
    if (!rect) return;

    // Start drag
    this._hasCustomView = true; // lock view to user interaction
    const idx = this.currentGlyphIndex;
    if (idx === null) return;
    const glyph: any = this.resourceData.definitions[idx];
    if (hit.type === 'none') {
      this._drag = {
        mode: 'pan',
        startMouseX: pos.x,
        startMouseY: pos.y,
        startRect: { ...rect },
        startViewOffsetX: this._viewOffsetX,
        startViewOffsetY: this._viewOffsetY,
      };
      canvas.style.cursor = 'grabbing';
    } else if (hit.type === 'offset') {
      this._drag = {
        mode: 'offset',
        startMouseX: pos.x,
        startMouseY: pos.y,
        startRect: { ...rect },
        startOffset: { x: glyph.x_offset || 0, y: glyph.y_offset || 0 },
      };
      this._previewOffset = { ...this._drag.startOffset! };
    } else if (hit.type === 'advance') {
      const startAdvance = glyph[this.advanceKey] ?? 0;
      this._drag = {
        mode: 'advance',
        startMouseX: pos.x,
        startMouseY: pos.y,
        startRect: { ...rect },
        startAdvance: startAdvance,
      };
      this._previewAdvance = startAdvance;
    } else {
      this._drag = {
        mode: hit.type === 'inside' ? 'move' : 'resize',
        edges: hit.edges,
        startMouseX: pos.x,
        startMouseY: pos.y,
        startRect: { ...rect },
      };
      // preview immediately
      this._previewRect = { ...rect };
    }
  }

  onFullCanvasMouseMove(evt: MouseEvent) {
    if (!this.resourceData || !this.fullBitmapCanvas) return;
    const canvas = this.fullBitmapCanvas.nativeElement;
    const pos = this.getMouseCanvasPos(evt, canvas);

    if (!this._drag) {
      const hit = this.hitTest(pos.x, pos.y);
      this.setCursorForHit(hit);
      return;
    }

    const drag = this._drag;

    if (drag.mode === 'pan') {
      this._viewOffsetX = drag.startViewOffsetX! + (pos.x - drag.startMouseX);
      this._viewOffsetY = drag.startViewOffsetY! + (pos.y - drag.startMouseY);
    } else if (drag.mode === 'offset') {
      const dx = (pos.x - drag.startMouseX) / this._viewRatio;
      const dy = (pos.y - drag.startMouseY) / this._viewRatio;
      // Moving origin point moves rectangle but we want to change x_offset/y_offset
      // x_offset = glyph.x - origin.x
      // x_offset_new = glyph.x - (origin.x + dx) = x_offset - dx
      this._previewOffset = {
        x: Math.round(drag.startOffset!.x - dx),
        y: Math.round(drag.startOffset!.y - dy),
      };
    } else if (drag.mode === 'advance') {
      const dx = (pos.x - drag.startMouseX) / this._viewRatio;
      this._previewAdvance = Math.round(drag.startAdvance! + dx);
    } else {
      const dx = (pos.x - drag.startMouseX) / this._viewRatio;
      const dy = (pos.y - drag.startMouseY) / this._viewRatio;

      if (drag.mode === 'move') {
        const nx = Math.round(drag.startRect.x + dx);
        const ny = Math.round(drag.startRect.y + dy);
        this._previewRect = { x: nx, y: ny, width: drag.startRect.width, height: drag.startRect.height };
      } else {
        // resize
        let x1 = drag.startRect.x;
        let y1 = drag.startRect.y;
        let x2 = drag.startRect.x + drag.startRect.width;
        let y2 = drag.startRect.y + drag.startRect.height;

        if (drag.edges?.l) x1 = Math.round(drag.startRect.x + dx);
        if (drag.edges?.r) x2 = Math.round(drag.startRect.x + drag.startRect.width + dx);
        if (drag.edges?.t) y1 = Math.round(drag.startRect.y + dy);
        if (drag.edges?.b) y2 = Math.round(drag.startRect.y + drag.startRect.height + dy);

        // Ensure minimum size 1px
        if (x2 - x1 < 1) {
          if (drag.edges?.l) x1 = x2 - 1;
          else x2 = x1 + 1;
        }
        if (y2 - y1 < 1) {
          if (drag.edges?.t) y1 = y2 - 1;
          else y2 = y1 + 1;
        }

        this._previewRect = { x: x1, y: y1, width: x2 - x1, height: y2 - y1 };
      }
    }

    // re-render
    this.renderFullBitmap(this.currentGlyphIndex);
  }

  onFullCanvasMouseUp(_evt: MouseEvent) {
    if (!this._drag || !this.resourceData) {
      this._drag = null;
      return;
    }

    if (this._drag.mode === 'pan') {
      this._drag = null;
      const canvas = this.fullBitmapCanvas?.nativeElement;
      if (canvas) {
        const pos = this.getMouseCanvasPos(_evt, canvas);
        const hit = this.hitTest(pos.x, pos.y);
        this.setCursorForHit(hit);
      }
      return;
    }

    const idx = this.currentGlyphIndex;
    if (idx === null) {
      this._drag = null;
      return;
    }
    const glyph: any = this.resourceData.definitions[idx];

    let changes: any[] = [];

    if (this._drag.mode === 'offset') {
      const offset = this._previewOffset || { x: glyph.x_offset || 0, y: glyph.y_offset || 0 };
      if (offset.x !== glyph.x_offset) {
        changes.push({
          op: 'set',
          id: joinId(this.resourceId!, 'definitions', idx, 'x_offset'),
          timestamp: Date.now(),
          oldValue: glyph.x_offset,
          newValue: offset.x,
        });
      }
      if (offset.y !== glyph.y_offset) {
        changes.push({
          op: 'set',
          id: joinId(this.resourceId!, 'definitions', idx, 'y_offset'),
          timestamp: Date.now(),
          oldValue: glyph.y_offset,
          newValue: offset.y,
        });
      }
    } else if (this._drag.mode === 'advance') {
      const key = this.advanceKey;
      const advance = this._previewAdvance ?? glyph[key] ?? 0;
      if (advance !== glyph[key]) {
        changes.push({
          op: 'set',
          id: joinId(this.resourceId!, 'definitions', idx, key),
          timestamp: Date.now(),
          oldValue: glyph[key],
          newValue: advance,
        });
      }
    } else {
      const rect = this._previewRect || { x: glyph.x, y: glyph.y, width: glyph.width, height: glyph.height };
      ['x', 'y', 'width', 'height'].forEach(key => {
        if ((rect as any)[key] !== glyph[key]) {
          changes.push({
            op: 'set',
            id: joinId(this.resourceId!, 'definitions', idx, key),
            timestamp: Date.now(),
            oldValue: glyph[key],
            newValue: (rect as any)[key],
          });
        }
      });
    }

    if (changes.length > 0) {
      this.emitNewChange({
        op: 'bundle',
        changes: changes,
      });
    }

    this._drag = null;
    this._previewRect = null;
    this._previewOffset = null;
    this._previewAdvance = null;
  }

  // frames the selected glyph again, as when it was selected
  fitCharPreview() {
    this._hasCustomView = false;
    this.renderFullBitmap(this.currentGlyphIndex);
  }

  // arrows move the glyph rectangle by 1 px, Shift+arrows resize it (right / down grow): one change per key
  onFullCanvasKeyDown(evt: KeyboardEvent) {
    const steps: { [key: string]: [number, number] } = {
      ArrowLeft: [-1, 0],
      ArrowRight: [1, 0],
      ArrowUp: [0, -1],
      ArrowDown: [0, 1],
    };
    const step = steps[evt.key];
    const idx = this.currentGlyphIndex;
    if (!step || idx === null || !this.resourceData || this._drag) return;
    const glyph: any = this.resourceData.definitions[idx];
    if (!glyph) return;
    evt.preventDefault();
    const [dx, dy] = step;
    const [key, value] = evt.shiftKey
      ? dx !== 0
        ? ['width', Math.max(1, glyph.width + dx)]
        : ['height', Math.max(1, glyph.height + dy)]
      : dx !== 0
        ? ['x', Math.max(0, glyph.x + dx)]
        : ['y', Math.max(0, glyph.y + dy)];
    if (value === glyph[key]) return;
    this.emitNewChange({
      op: 'set',
      id: joinId(this.resourceId!, 'definitions', idx, key),
      oldValue: glyph[key],
      newValue: value,
    });
  }

  _glyphSearch = '';
  _kerningSearch = '';
  _glyphSearchMessage = '';
  _kerningSearchMessage = '';

  // a typed character ("A", "가"), a code (65) or a hex code (0x41, U+AC00)
  private searchCode(query: string): number | null {
    const q = query.trim();
    if (!q) return null;
    const hex = /^(?:0x|u\+)([0-9a-f]+)$/i.exec(q);
    if (hex) return parseInt(hex[1], 16);
    const chars = Array.from(q);
    if (chars.length === 1) return chars[0].codePointAt(0)!;
    if (/^\d+$/.test(q)) return parseInt(q, 10);
    return null;
  }

  private describeCode(code: number): string {
    return `"${this.getSymbol(code)}" (${code}, 0x${code.toString(16).toUpperCase()})`;
  }

  findGlyph(query: string) {
    const code = this.searchCode(query);
    if (code === null) {
      this._glyphSearchMessage = query.trim() ? 'Type a character, a code (65) or a hex code (0x41)' : '';
      return;
    }
    const index = (this.resourceData?.definitions || []).findIndex((g: any) => g.code === code);
    if (index < 0) {
      this._glyphSearchMessage = `No glyph for ${this.describeCode(code)}`;
      return;
    }
    this._glyphSearchMessage = '';
    this._hasCustomView = false;
    this._previewRect = null;
    this.onGlyphSelectedIndexChange(index);
    this.glyphsTable?.showItem(index);
  }

  private _lastKerningSearchCode: number | null = null;

  // the next pair (after the selected one) with the glyph on either side
  findKerning(query: string) {
    const code = this.searchCode(query);
    if (code === null) {
      this._kerningSearchMessage = query.trim() ? 'Type a character, a code (65) or a hex code (0x41)' : '';
      return;
    }
    const kernings: any[] = this.resourceData?.kernings || [];
    const matches = kernings.map((k, i) => (k.left === code || k.right === code ? i : -1)).filter(i => i >= 0);
    if (!matches.length) {
      this._kerningSearchMessage = `No pairs with ${this.describeCode(code)}`;
      return;
    }
    // a new search starts at the first pair, the same one again goes on after the selected pair
    const selected = code === this._lastKerningSearchCode ? (this._selectedKerningIndex$.getValue() ?? -1) : -1;
    this._lastKerningSearchCode = code;
    const index = matches.find(i => i > selected) ?? matches[0];
    this._kerningSearchMessage = `Pair ${matches.indexOf(index) + 1} of ${matches.length} with ${this.describeCode(code)}`;
    this.onKerningSelectedIndexChange(index);
    this.kerningsTable?.showItem(index);
  }

  onFullCanvasWheel(evt: WheelEvent) {
    if (!this.fullBitmapCanvas || !this._image) return;
    evt.preventDefault();
    const canvas = this.fullBitmapCanvas.nativeElement;
    const pos = this.getMouseCanvasPos(evt as unknown as MouseEvent, canvas);

    // Anchor image coords under cursor
    const imgPt = this.canvasToImage(pos.x, pos.y);

    const zoomFactor = Math.pow(1.25, -evt.deltaY / 100);
    const minZoom = 0.05;
    const maxZoom = 32;
    let newRatio = this._viewRatio * zoomFactor;
    newRatio = Math.max(minZoom, Math.min(maxZoom, newRatio));

    // Update view to keep anchor stable
    this._viewOffsetX = pos.x - imgPt.x * newRatio;
    this._viewOffsetY = pos.y - imgPt.y * newRatio;
    this._viewRatio = newRatio;
    this._hasCustomView = true;

    this.renderFullBitmap(this.currentGlyphIndex);
  }

  private renderTextPreview(text: string) {
    if (!this.resourceData) return;
    const canvas = this.textPreviewCanvas.nativeElement;
    const ctx = canvas.getContext('2d');
    if (!ctx || !this._image) return;

    const definitions: any[] = this.resourceData.definitions;
    const kernings: any[] = this.resourceData.kernings || [];

    const charMap = new Map<number, any>();
    for (const def of definitions) {
      charMap.set(def.code, def);
    }

    const kerningMap = new Map<string, number>();
    for (const kern of kernings) {
      kerningMap.set(`${kern.left}_${kern.right}`, kern.kerning);
    }

    const lines = text.split('\n');
    // y_offset is measured from the top of the line: NFS6 capitals end at ascent, descenders at ascent + descent.
    // Fonts with descent 0 (TNFS, NFS2) keep the whole line height in ascent
    const lineHeight = this.resourceData.ascent + this.resourceData.descent || 32;
    const padding = 20;
    // a character the font has no glyph for: a hatched box (a gap for whitespace), listed under the text
    // where most glyphs start and end (capitals), from the line top: TNFS fonts keep the line height in ascent
    const mostCommon = (values: number[]) => {
      const counts = new Map<number, number>();
      values.forEach(v => counts.set(v, (counts.get(v) || 0) + 1));
      return Array.from(counts.entries()).sort((a, b) => b[1] - a[1] || a[0] - b[0])[0]?.[0];
    };
    const drawn = definitions.filter((g: any) => g.width > 1 && g.height > 1);
    const missingTop = mostCommon(drawn.map((g: any) => g.y_offset || 0)) ?? 0;
    const missingBottom = mostCommon(drawn.map((g: any) => (g.y_offset || 0) + g.height)) ?? lineHeight;
    const missingHeight = Math.max(4, missingBottom - missingTop);
    const missingWidth = Math.max(4, Math.round(missingHeight * 0.6));

    // lay out first: the canvas gets the width of the widest line (the container scrolls)
    type Item = { x: number; glyph?: any; missing?: boolean };
    const laidOut: Item[][] = [];
    const missing = new Set<string>();
    let maxLineWidth = 0;
    for (const line of lines) {
      const items: Item[] = [];
      let cursorX = 0;
      let prevCharCode: number | null = null;
      for (const char of Array.from(line)) {
        const charCode = char.codePointAt(0)!;
        const glyph = charMap.get(charCode);
        if (glyph) {
          if (prevCharCode !== null) {
            cursorX += kerningMap.get(`${prevCharCode}_${charCode}`) || 0;
          }
          items.push({ x: cursorX, glyph });
          cursorX += glyph[this.advanceKey] || 0;
          prevCharCode = charCode;
        } else {
          missing.add(char);
          if (/\s/.test(char)) {
            cursorX += lineHeight * 0.3;
          } else {
            items.push({ x: cursorX, missing: true });
            cursorX += missingWidth + 2;
          }
          prevCharCode = null;
        }
        maxLineWidth = Math.max(maxLineWidth, cursorX);
      }
      laidOut.push(items);
    }
    const missingSymbols = Array.from(missing).map(x => (x === ' ' ? 'space' : x === '\t' ? 'tab' : x));
    if (missingSymbols.join('\n') !== this._missingSymbols.join('\n')) {
      this._missingSymbols = missingSymbols;
      this.cdr.markForCheck();
    }

    const containerWidth = canvas.parentElement?.clientWidth || 800;
    canvas.width = Math.max(containerWidth, Math.ceil(maxLineWidth) + padding * 2);
    canvas.height = Math.max(padding * 2 + lines.length * lineHeight, 200);

    ctx.fillStyle = 'black';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    ctx.imageSmoothingEnabled = false;

    let cursorY = padding;
    for (const items of laidOut) {
      for (const item of items) {
        const x = padding + item.x;
        if (item.missing) {
          this.drawMissingGlyph(ctx, x, cursorY + missingTop, missingWidth, missingHeight);
          continue;
        }
        const glyph = item.glyph;
        ctx.drawImage(
          this._image,
          glyph.x,
          glyph.y,
          glyph.width,
          glyph.height,
          x + (glyph.x_offset || 0),
          cursorY + (glyph.y_offset || 0),
          glyph.width,
          glyph.height,
        );
      }
      cursorY += lineHeight;
    }
  }

  private drawMissingGlyph(ctx: CanvasRenderingContext2D, x: number, y: number, width: number, height: number) {
    ctx.save();
    ctx.strokeStyle = '#ff5252';
    ctx.lineWidth = 1;
    ctx.strokeRect(x + 0.5, y + 0.5, width - 1, height - 1);
    ctx.beginPath();
    ctx.rect(x, y, width, height);
    ctx.clip();
    ctx.beginPath();
    for (let d = -height; d < width; d += 4) {
      ctx.moveTo(x + d, y + height);
      ctx.lineTo(x + d + height, y);
    }
    ctx.stroke();
    ctx.restore();
  }

  // characters of the preview text the font has no glyph for
  _missingSymbols: string[] = [];

  readonly textPresets: { label: string; title: string }[] = [
    { label: 'Sample', title: 'Pangram, digits and punctuation' },
    { label: 'A–Z', title: 'Capital letters' },
    { label: 'a–z', title: 'Small letters' },
    { label: '0–9', title: 'Digits' },
    { label: 'All', title: 'Every glyph of the font, by code' },
  ];

  setTextPreset(label: string) {
    const range = (from: string, to: string) =>
      Array.from({ length: to.charCodeAt(0) - from.charCodeAt(0) + 1 }, (_, i) =>
        String.fromCharCode(from.charCodeAt(0) + i),
      ).join('');
    let text = FontBlockUiComponent.SAMPLE_TEXT;
    if (label === 'A–Z') text = range('A', 'Z');
    else if (label === 'a–z') text = range('a', 'z');
    else if (label === '0–9') text = range('0', '9');
    else if (label === 'All') {
      const symbols = [...(this.resourceData?.definitions || [])]
        .map((g: any) => g.code)
        .sort((a: number, b: number) => a - b)
        .map((code: number) => this.getSymbol(code))
        .filter((s: string) => s && !/\s/.test(s));
      const lines: string[] = [];
      for (let i = 0; i < symbols.length; i += 16) lines.push(symbols.slice(i, i + 16).join(''));
      text = lines.join('\n');
    }
    this._text$.next(text);
  }

  private updateColumns() {
    if (!this.resourceSchema || !this.resourceData) return;

    const gSchema = this.resourceSchema.fields.find((f: any) => f.name === 'definitions')?.schema;
    const gItemSchema = gSchema?.child_schema;
    if (gItemSchema) {
      this._glyphColumns = [
        { key: 'symbol', index: -1, schema: { block_class_mro: 'UTF8Block__' } },
        ...gItemSchema.fields
          .filter((f: any) => {
            if (f.name === 'num_kern') return this.resourceData.version > 309;
            if (f.name === 'pad') return this.resourceData.version <= 309 && this.resourceData.version >= 200;
            if (f.name === 'kern_index')
              return this.resourceData.version >= 321 && this.resourceData.flags.format === '16-bytes';
            if (f.name === 'x_advance')
              return this.resourceData.version >= 321 && this.resourceData.flags.format === '16-bytes';
            return true;
          })
          // programmatic fields (num_kern, kern_index) are recomputed on save: shown read-only with hidden fields
          .filter((f: any) => !this._hideHiddenFields || !f.schema.is_programmatic)
          .map((f: any, i: number) => ({
            key: f.name,
            index: i,
            schema: f.schema,
            readonly: !!f.schema.is_programmatic,
          })),
      ];
    }

    const kSchema = this.resourceSchema.fields.find((f: any) => f.name === 'kernings')?.schema;
    const kItemSchema = kSchema?.child_schema;
    if (kItemSchema) {
      this._kerningColumns = [
        { key: 'Left Symbol', index: -1, schema: { block_class_mro: 'UTF8Block__' } },
        { key: 'Right Symbol', index: -1, schema: { block_class_mro: 'UTF8Block__' } },
        ...kItemSchema.fields.map((f: any, i: number) => {
          let key = f.name;
          if (key === 'left') key = 'Left Symbol Code';
          else if (key === 'right') key = 'Right Symbol Code';
          else if (key === 'kerning') key = 'Kerning';
          else if (key === 'unk') key = 'Unk';
          return { key, index: i, schema: f.schema };
        }),
      ];
    }
  }

  async addGlyph() {
    const rid = joinId(this.resourceId!, 'definitions');
    const newItem = await this.mainService.getNewItemData(rid);
    // the next code after the last glyph keeps the glyphs sorted
    const definitions = this.resourceData!.definitions;
    if (definitions.length > 0) {
      newItem.code = Math.min(definitions[definitions.length - 1].code + 1, 0xffff);
    }
    this.changes
      .appendChanges({
        timestamp: Date.now(),
        id: rid,
        op: 'array_insert',
        index: this.resourceData!.definitions.length,
        value: newItem,
      })
      .then();
  }

  removeGlyph(index: number) {
    if (this.currentGlyphIndex === index) {
      this.onGlyphSelectedIndexChange(null);
    }
    this.changes
      .appendChanges({
        timestamp: Date.now(),
        id: joinId(this.resourceId!, 'definitions'),
        op: 'array_remove',
        index,
        oldValue: this.resourceData!.definitions[index],
      })
      .then();
  }

  private symbolInputToCode(input: string, oldCode: number): number | undefined {
    if (input && input.length) {
      let charCode = oldCode;
      // code points, so a character above U+FFFF gets its own code (and a range message), not a surrogate's
      for (const char of Array.from(input)) {
        if (char.codePointAt(0) !== oldCode) {
          charCode = char.codePointAt(0)!;
        }
      }
      if (charCode !== undefined && !isNaN(charCode) && charCode !== oldCode) {
        return charCode;
      }
    }
    return undefined;
  }

  // sets a field of a glyph / kerning. A changed sort field moves the item to its sorted place in the same undo step,
  // then the table shows and selects it there
  private setItemValue(arrayName: 'definitions' | 'kernings', index: number, field: string, newValue: any) {
    const array = this.resourceData![arrayName];
    const arrayId = joinId(this.resourceId!, arrayName);
    const timestamp = Date.now();
    const changes: ChangeEntry[] = [
      { timestamp, id: joinId(arrayId, index, field), op: 'set', oldValue: array[index][field], newValue },
    ];
    const sortField = arrayName === 'definitions' ? 'code' : this.kerningsSortField;
    const target = field === sortField ? sortedPosition(array, field, newValue, index) : index;
    if (target !== index) {
      const item = array[index];
      changes.push(
        { timestamp, id: arrayId, op: 'array_remove', index, oldValue: item },
        { timestamp, id: arrayId, op: 'array_insert', index: target, value: item },
      );
    }
    this.changes
      .appendChanges(changes.length === 1 ? changes[0] : { timestamp, id: arrayId, op: 'bundle', changes })
      .then();
    if (target !== index) {
      // the edited input now shows another item
      (document.activeElement as HTMLElement | null)?.blur();
      if (arrayName === 'definitions') {
        this._hasCustomView = false;
        this._previewRect = null;
        this.onGlyphSelectedIndexChange(target);
        this.glyphsTable?.showItem(target);
      } else {
        this.onKerningSelectedIndexChange(target);
        this.kerningsTable?.showItem(target);
      }
    }
  }

  // a symbol typed for a glyph / kerning code must fit the field (kerning right glyph is 1 byte)
  private symbolRangeError(arrayName: 'definitions' | 'kernings', field: string, label: string, code: number) {
    const arraySchema = this.resourceSchema?.fields.find((f: any) => f.name === arrayName)?.schema;
    const range = numberRange(arraySchema?.child_schema?.fields.find((f: any) => f.name === field)?.schema);
    if ((range.max !== null && code > range.max) || (range.min !== null && code < range.min)) {
      return `${label} code must be ${range.min}..${range.max}: "${this.getSymbol(code)}" is ${code}`;
    }
    return null;
  }

  // a glyph code must fit the field and be unique: the edit is refused, the table puts the old value back
  validateGlyphChange = (index: number, field: string | null, _subField: string | null, value: any): string | null => {
    const definitions = this.resourceData!.definitions;
    let code: number | undefined;
    if (field === 'symbol') code = this.symbolInputToCode(value, definitions[index].code);
    else if (field === 'code') code = +value;
    if (code === undefined) return null;
    if (field === 'symbol') {
      const rangeError = this.symbolRangeError('definitions', 'code', 'Glyph', code);
      if (rangeError) return rangeError;
    }
    const other = definitions.findIndex((g: any, i: number) => i !== index && g.code === code);
    if (other < 0) return null;
    return `Code ${code} ("${this.getSymbol(code)}") is already used by glyph #${other}`;
  };

  validateKerningChange = (
    index: number,
    field: string | null,
    _subField: string | null,
    value: any,
  ): string | null => {
    if (field !== 'Left Symbol' && field !== 'Right Symbol') return null;
    const dataField = field === 'Left Symbol' ? 'left' : 'right';
    const code = this.symbolInputToCode(value, this.resourceData!.kernings[index][dataField]);
    if (code === undefined) return null;
    return this.symbolRangeError('kernings', dataField, field === 'Left Symbol' ? 'Left glyph' : 'Right glyph', code);
  };

  // sorts glyphs by code (or kernings by right glyph) in one undo step, the selected item stays selected
  sortItems(arrayName: 'definitions' | 'kernings') {
    const array: any[] = this.resourceData![arrayName];
    const sortField = arrayName === 'definitions' ? 'code' : 'right';
    const sorted = [...array].sort((a, b) => a[sortField] - b[sortField]);
    const timestamp = Date.now();
    const changes: ChangeEntry[] = sorted
      .map((item, i): ChangeEntry | null =>
        item === array[i]
          ? null
          : { timestamp, id: joinId(this.resourceId!, arrayName, i), op: 'set', oldValue: array[i], newValue: item },
      )
      .filter((c): c is ChangeEntry => c !== null);
    if (changes.length === 0) return;
    const selected$ = arrayName === 'definitions' ? this._selectedGlyphIndex$ : this._selectedKerningIndex$;
    const selectedItem = selected$.getValue() !== null ? array[selected$.getValue()!] : null;
    this.changes.appendChanges({ timestamp, id: joinId(this.resourceId!, arrayName), op: 'bundle', changes }).then();
    if (selectedItem) {
      const index = sorted.indexOf(selectedItem);
      selected$.next(index);
      (arrayName === 'definitions' ? this.glyphsTable : this.kerningsTable)?.showItem(index);
    }
  }

  onGlyphDataChanged(event: { index: number; field: string | null; subField: string | null; value: any }) {
    if (event.field === 'symbol') {
      const charCode = this.symbolInputToCode(event.value, this.resourceData!.definitions[event.index]['code']);
      if (charCode !== undefined) {
        this.setItemValue('definitions', event.index, 'code', charCode);
      }
      return;
    }
    if (event.field) {
      this.setItemValue('definitions', event.index, event.field, event.value);
    }
  }

  async addKerning() {
    const rid = joinId(this.resourceId!, 'kernings');
    const newItem = await this.mainService.getNewItemData(rid);
    // the right glyph of the last pair keeps the pairs sorted
    const kernings = this.resourceData!.kernings || [];
    if (this.kerningsSortField && kernings.length > 0) {
      newItem.right = kernings[kernings.length - 1].right;
    }
    this.changes
      .appendChanges({
        timestamp: Date.now(),
        id: rid,
        op: 'array_insert',
        index: this.resourceData!.kernings.length,
        value: newItem,
      })
      .then();
  }

  removeKerning(index: number) {
    if (this._selectedKerningIndex$.getValue() === index) {
      this.onKerningSelectedIndexChange(null);
    }
    this.changes
      .appendChanges({
        timestamp: Date.now(),
        id: joinId(this.resourceId!, 'kernings'),
        op: 'array_remove',
        index,
        oldValue: this.resourceData!.kernings[index],
      })
      .then();
  }

  moveKerningUp(index: number) {
    const currentIndex = this._selectedKerningIndex$.getValue();
    if (currentIndex === index) {
      this.onKerningSelectedIndexChange(index - 1);
    } else if (currentIndex === index - 1) {
      this.onKerningSelectedIndexChange(index);
    }
    this.changes
      .appendChanges({
        timestamp: Date.now(),
        id: joinId(this.resourceId!, 'kernings'),
        op: 'array_swap',
        indexA: index,
        indexB: index - 1,
      })
      .then();
  }

  moveKerningDown(index: number) {
    const currentIndex = this._selectedKerningIndex$.getValue();
    if (currentIndex === index) {
      this.onKerningSelectedIndexChange(index + 1);
    } else if (currentIndex === index + 1) {
      this.onKerningSelectedIndexChange(index);
    }
    this.changes
      .appendChanges({
        timestamp: Date.now(),
        id: joinId(this.resourceId!, 'kernings'),
        op: 'array_swap',
        indexA: index,
        indexB: index + 1,
      })
      .then();
  }

  onKerningDataChanged(event: { index: number; field: string | null; subField: string | null; value: any }) {
    if (event.field === 'Left Symbol' || event.field === 'Right Symbol') {
      const dataField = event.field === 'Left Symbol' ? 'left' : 'right';
      const charCode = this.symbolInputToCode(event.value, this.resourceData!.kernings[event.index][dataField]);
      if (charCode !== undefined) {
        this.setItemValue('kernings', event.index, dataField, charCode);
      }
      return;
    }
    if (event.field) {
      // Mapping back from DataTable display keys to data keys if necessary
      let dataField = event.field;
      if (dataField === 'Left Symbol Code') dataField = 'left';
      else if (dataField === 'Right Symbol Code') dataField = 'right';
      else if (dataField === 'Kerning') dataField = 'kerning';
      else if (dataField === 'Unk') dataField = 'unk';
      this.setItemValue('kernings', event.index, dataField, event.value);
    }
  }

  onGlyphFocused(event: [string[], number]) {
    // Reset view to auto-focus new glyph
    this._hasCustomView = false;
    this._previewRect = null;
    this.onGlyphSelectedIndexChange(event[1]);
  }

  onGlyphSelectedIndexChange(index: number | null) {
    this._selectedGlyphIndex$.next(index);
  }

  onKerningFocused(event: [string[], number]) {
    this.onKerningSelectedIndexChange(event[1]);
  }

  onKerningSelectedIndexChange(index: number | null) {
    this._selectedKerningIndex$.next(index);
  }

  onTextChange(event: Event) {
    this._text$.next((event.target as HTMLTextAreaElement).value);
  }

  getSymbol(code: any): string {
    try {
      const codepoint = parseInt(code, 10);
      if (isNaN(codepoint)) return '';
      return String.fromCodePoint(codepoint);
    } catch (e) {
      return '';
    }
  }

  override ngOnDestroy(): void {
    super.ngOnDestroy();
    this.destroyed$.next();
    this.destroyed$.complete();
    this._imageRefreshed$.complete();
    if (this._resizeObserver) {
      this._resizeObserver.disconnect();
    }
  }

  protected readonly joinId = joinId;
}
