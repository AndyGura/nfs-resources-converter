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
import { ArrayTableColumn } from '../../common/data-table/data-table.component';
import { joinId } from '../../../../utils/join-id';
import { SubscribableGuiComponent } from '../../gui.component';
import { ChangeEntryPayload } from '../../../../services/changes.service';

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
  _text$: BehaviorSubject<string> = new BehaviorSubject<string>(
    'The quick brown fox jumps over the lazy dog\n0123456789\n!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~',
  );

  _glyphColumns: ArrayTableColumn[] = [];
  _kerningColumns: ArrayTableColumn[] = [];

  public _glyphsWithSymbols$ = new BehaviorSubject<any[]>([]);
  public _kerningsWithSymbols$ = new BehaviorSubject<any[]>([]);
  public _glyphPageSize = 100;
  public _glyphPageIndex = 0;
  public _kerningPageSize = 100;
  public _kerningPageIndex = 0;

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
    const glyphs = this.resourceData.definitions.map((g: any) => ({ ...g, symbol: this.getSymbol(g.code) }));
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

  bitmapSchema() {
    return (this.resourceSchema.fields || []).find((x: { name: string; schema: BlockSchema }) => x.name === 'bitmap')
      ?.schema;
  }

  readonly ngZone = inject(NgZone);

  async ngAfterViewInit(): Promise<void> {
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
    this._resizeObserver.observe(this.textPreviewCanvas.nativeElement);

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
      const x_advance = glyph.x_advance || 0;

      // Origin point in image coordinates
      const originX = glyph.x - x_offset;
      const originY = glyph.y - y_offset;

      // The area we want to focus on (in image coordinates)
      const minX = Math.min(glyph.x, originX, originX + x_advance);
      const maxX = Math.max(glyph.x + glyph.width, originX, originX + x_advance);
      const minY = Math.min(glyph.y, originY, originY + (glyph.advance || 0));
      const maxY = Math.max(glyph.y + glyph.height, originY, originY + (glyph.advance || 0));

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
      let xAdvance = this._previewAdvance;
      if (xAdvance === null) {
        if (glyph.x_advance !== undefined && glyph.x_advance !== 0) {
          xAdvance = glyph.x_advance;
        } else {
          xAdvance = glyph.advance ?? 0;
        }
      }
      if (xAdvance !== undefined && xAdvance !== null) {
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
      }

      // Draw vertical advance if present
      if (glyph.x_advance !== undefined && glyph.advance !== 0) {
        ctx.strokeStyle = '#ff40ff';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(originCanvasX, originCanvasY);
        ctx.lineTo(originCanvasX, originCanvasY + glyph.advance * ratio);
        ctx.stroke();

        // Little tick at the end of vertical advance
        ctx.beginPath();
        ctx.moveTo(originCanvasX - 5, originCanvasY + glyph.advance * ratio);
        ctx.lineTo(originCanvasX + 5, originCanvasY + glyph.advance * ratio);
        ctx.stroke();
      }
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
    let xAdvance = this._previewAdvance;
    if (xAdvance === null) {
      if (glyph.x_advance !== undefined && glyph.x_advance !== 0) {
        xAdvance = glyph.x_advance;
      } else {
        xAdvance = glyph.advance ?? 0;
      }
    }
    if (xAdvance !== undefined && xAdvance !== null) {
      const advanceEndX = originCanvasX + xAdvance * ratio;
      if (Math.abs(canvasX - advanceEndX) <= 8 && Math.abs(canvasY - originCanvasY) <= 12) {
        return { type: 'advance' };
      }
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
      let startAdvance = glyph.x_advance;
      if (startAdvance === undefined || startAdvance === 0) {
        startAdvance = glyph.advance ?? 0;
      }
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
      let advance = this._previewAdvance;
      if (advance === null) {
        advance = glyph.x_advance !== undefined && glyph.x_advance !== 0 ? glyph.x_advance : (glyph.advance ?? 0);
      }
      const key = glyph.x_advance !== undefined && glyph.x_advance !== 0 ? 'x_advance' : 'advance';
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

  onFullCanvasWheel(evt: WheelEvent) {
    if (!this.fullBitmapCanvas || !this._image) return;
    evt.preventDefault();
    const canvas = this.fullBitmapCanvas.nativeElement;
    const pos = this.getMouseCanvasPos(evt as unknown as MouseEvent, canvas);

    // Anchor image coords under cursor
    const imgPt = this.canvasToImage(pos.x, pos.y);

    const zoomFactor = Math.pow(1.8, -evt.deltaY / 100);
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
    const lineHeight = this.resourceData.line_height || 32;
    const padding = 20;

    // Measure text to set canvas height
    let totalHeight = padding * 2;
    for (let i = 0; i < lines.length; i++) {
      totalHeight += lineHeight;
    }

    const canvasWidth = canvas.parentElement?.clientWidth || 800;
    canvas.width = canvasWidth;
    canvas.height = Math.max(totalHeight, 200);

    ctx.fillStyle = 'black';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    ctx.imageSmoothingEnabled = false;

    let cursorY = padding + (this.resourceData.base || lineHeight * 0.8);

    for (const line of lines) {
      let cursorX = padding;
      let prevCharCode: number | null = null;

      for (let i = 0; i < line.length; i++) {
        const charCode = line.charCodeAt(i);
        const glyph = charMap.get(charCode);

        if (glyph) {
          if (prevCharCode !== null) {
            const kerning = kerningMap.get(`${prevCharCode}_${charCode}`) || 0;
            cursorX += kerning;
          }

          const x = cursorX + (glyph.x_offset || 0);
          const y = cursorY + (glyph.y_offset || 0) - (this.resourceData.base || lineHeight * 0.8);

          ctx.drawImage(this._image, glyph.x, glyph.y, glyph.width, glyph.height, x, y, glyph.width, glyph.height);

          cursorX += glyph.x_advance || glyph.advance || 0;
          prevCharCode = charCode;
        } else {
          // Fallback for space or missing characters
          cursorX += lineHeight * 0.3;
          prevCharCode = null;
        }
      }
      cursorY += lineHeight;
    }
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
            if (f.name === 'num_kern') return this.resourceData.version >= 300;
            if (f.name === 'pad') return this.resourceData.version < 300 && this.resourceData.version >= 200;
            if (f.name === 'kern_index')
              return this.resourceData.version >= 321 && this.resourceData.flags.format === '16-bytes';
            if (f.name === 'x_advance')
              return this.resourceData.version >= 321 && this.resourceData.flags.format === '16-bytes';
            return true;
          })
          .map((f: any, i: number) => ({ key: f.name, index: i, schema: f.schema })),
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

  moveGlyphUp(index: number) {
    if (this.currentGlyphIndex === index) {
      this.onGlyphSelectedIndexChange(index - 1);
    } else if (this.currentGlyphIndex === index - 1) {
      this.onGlyphSelectedIndexChange(index);
    }
    this.changes
      .appendChanges({
        timestamp: Date.now(),
        id: joinId(this.resourceId!, 'definitions'),
        op: 'array_swap',
        indexA: index,
        indexB: index - 1,
      })
      .then();
  }

  moveGlyphDown(index: number) {
    if (this.currentGlyphIndex === index) {
      this.onGlyphSelectedIndexChange(index + 1);
    } else if (this.currentGlyphIndex === index + 1) {
      this.onGlyphSelectedIndexChange(index);
    }
    this.changes
      .appendChanges({
        timestamp: Date.now(),
        id: joinId(this.resourceId!, 'definitions'),
        op: 'array_swap',
        indexA: index,
        indexB: index + 1,
      })
      .then();
  }

  onGlyphDataChanged(event: { index: number; field: string | null; subField: string | null; value: any }) {
    if (event.field === 'symbol') {
      if (!event.value) return;
      let oldCode = this.resourceData!.definitions[event.index]['code'];
      let charCode = oldCode;
      for (let i = 0; i < event.value.length; i++) {
        if (event.value.charCodeAt(i) !== oldCode) {
          charCode = event.value.charCodeAt(i);
        }
      }
      if (charCode !== undefined && !isNaN(charCode) && charCode !== oldCode) {
        const change = {
          timestamp: Date.now(),
          id: joinId(this.resourceId!, 'definitions', event.index, 'code'),
          op: 'set',
          oldValue: this.resourceData!.definitions[event.index]['code'],
          newValue: charCode,
        };
        this.changes.appendChanges(change as any).then();
      }
      return;
    }
    if (event.field) {
      this.changes
        .appendChanges({
          timestamp: Date.now(),
          id: joinId(this.resourceId!, 'definitions', event.index, event.field),
          op: 'set',
          oldValue: this.resourceData!.definitions[event.index][event.field],
          newValue: event.value,
        })
        .then();
    }
  }

  async addKerning() {
    const rid = joinId(this.resourceId!, 'kernings');
    const newItem = await this.mainService.getNewItemData(rid);
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
      const charCode = event.value?.charCodeAt(0);
      if (charCode !== undefined && !isNaN(charCode)) {
        const dataField = event.field === 'Left Symbol' ? 'left' : 'right';
        this.changes
          .appendChanges({
            timestamp: Date.now(),
            id: joinId(this.resourceId!, 'kernings', event.index, dataField),
            op: 'set',
            oldValue: this.resourceData!.kernings[event.index][dataField],
            newValue: charCode,
          })
          .then();
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
      this.changes
        .appendChanges({
          timestamp: Date.now(),
          id: joinId(this.resourceId!, 'kernings', event.index, dataField),
          op: 'set',
          oldValue: this.resourceData!.kernings[event.index][dataField],
          newValue: event.value,
        })
        .then();
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
