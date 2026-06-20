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
import { getChildResource } from '../../../../utils/get-child-resource';
import { SubscribableGuiComponent } from '../../gui.component';
import { isNaN, parseInt } from 'lodash';

@Component({
  selector: 'app-font-block-ui',
  templateUrl: './font.block-ui.component.html',
  styleUrls: ['./font.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.Eager,
  standalone: false,
})
export class FontBlockUiComponent extends SubscribableGuiComponent implements AfterViewInit {
  @ViewChild('fullBitmapCanvas') fullBitmapCanvas!: ElementRef<HTMLCanvasElement>;
  @ViewChild('textPreviewCanvas') textPreviewCanvas!: ElementRef<HTMLCanvasElement>;

  _selectedGlyphIndex$: BehaviorSubject<number> = new BehaviorSubject<number>(0);
  _text$: BehaviorSubject<string> = new BehaviorSubject<string>(
    'The quick brown fox jumps over the lazy dog\n0123456789\n!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~',
  );

  _glyphColumns: ArrayTableColumn[] = [];
  _kerningColumns: ArrayTableColumn[] = [];

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
  }

  private readonly destroyed$: Subject<void> = new Subject<void>();
  private _image: HTMLImageElement | null = null;
  private _imageRefreshed$: Subject<void> = new Subject<void>();
  private _resizeObserver: ResizeObserver | null = null;
  private _resized$: Subject<void> = new Subject<void>();

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
        filter(x => !!this.resourceId && x.startsWith(joinId(this.resourceId, `bitmap`))),
      )
      .subscribe(() => {
        this.refreshImage().then();
      });

    this._resizeObserver = new ResizeObserver(() => {
      this._resized$.next();
    });
    this._resizeObserver.observe(this.fullBitmapCanvas.nativeElement);
    this._resizeObserver.observe(this.textPreviewCanvas.nativeElement);
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

  private renderFullBitmap(index: number) {
    if (!this.resourceData) return;
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
      const ratio = Math.min(scaleX, scaleY);

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

      ctx.drawImage(this._image!, offsetX, offsetY, imgWidth * ratio, imgHeight * ratio);

      const glyphCanvasX = offsetX + glyph.x * ratio;
      const glyphCanvasY = offsetY + glyph.y * ratio;
      const glyphCanvasW = glyph.width * ratio;
      const glyphCanvasH = glyph.height * ratio;

      // Draw bounding box
      ctx.strokeStyle = 'red';
      ctx.lineWidth = 2;
      ctx.strokeRect(glyphCanvasX, glyphCanvasY, glyphCanvasW, glyphCanvasH);

      // Draw offset (x_offset, y_offset)
      // Usually offset is relative to the "origin" of the glyph.
      // If we consider (glyphCanvasX, glyphCanvasY) to be the top-left of the image in the atlas,
      // the "origin" (baseline point) would be at (glyphCanvasX - x_offset*ratio, glyphCanvasY - y_offset*ratio)
      // Wait, usually x_offset and y_offset are added to the current pen position to get the top-left corner of the glyph image.
      // So: image_pos = pen_pos + offset => pen_pos = image_pos - offset
      const originCanvasX = glyphCanvasX - (glyph.x_offset || 0) * ratio;
      const originCanvasY = glyphCanvasY - (glyph.y_offset || 0) * ratio;

      // Draw origin point (Green)
      ctx.fillStyle = '#00ff00';
      ctx.beginPath();
      ctx.arc(originCanvasX, originCanvasY, 3, 0, Math.PI * 2);
      ctx.fill();

      // Draw advance (Blue)
      // Advance is usually from the origin.
      let xAdvance = glyph.x_advance || glyph.advance;
      if (xAdvance !== undefined) {
        ctx.strokeStyle = '#4040ff';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(originCanvasX, originCanvasY);
        ctx.lineTo(originCanvasX + xAdvance * ratio, originCanvasY);
        ctx.stroke();

        // Little tick at the end of advance
        ctx.beginPath();
        ctx.moveTo(originCanvasX + xAdvance * ratio, originCanvasY - 5);
        ctx.lineTo(originCanvasX + xAdvance * ratio, originCanvasY + 5);
        ctx.stroke();
      }

      // Draw vertical advance (advance means "y_advance" if x_advance is presen)
      if (glyph.x_advance !== undefined && glyph.advance !== 0) {
        ctx.strokeStyle = '#ff40ff'; // Purple/Magenta for vertical advance
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
    if (this.resourceData.definitions.length > 0) {
      const gSchema = this.resourceSchema.fields.find((f: any) => f.name === 'definitions')?.schema;
      const gItemSchema = gSchema?.child_schema;
      if (gItemSchema) {
        this._glyphColumns = [
          { key: 'symbol', index: -1, readonly: true, schema: { block_class_mro: 'UTF8Block__' } },
          ...gItemSchema.fields.map((f: any, i: number) => ({ key: f.name, index: i, schema: f.schema })),
        ];
      }
    }

    if (this.resourceData.kernings.length > 0) {
      const kSchema = this.resourceSchema.fields.find((f: any) => f.name === 'kernings')?.schema;
      const kItemSchema = kSchema?.child_schema;
      if (kItemSchema) {
        this._kerningColumns = [
          { key: 'Left Symbol', index: -1, readonly: true, schema: { block_class_mro: 'UTF8Block__' } },
          { key: 'Right Symbol', index: -1, readonly: true, schema: { block_class_mro: 'UTF8Block__' } },
          ...kItemSchema.fields.map((f: any, i: number) => {
            let key = f.key;
            if (key === 'left') key = 'Left Symbol Code';
            else if (key === 'right') key = 'Right Symbol Code';
            else if (key === 'kerning') key = 'Kerning';
            else if (key === 'unk') key = 'Unk';
            return { key, index: i, schema: f.schema };
          }),
        ];
      }
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
    if (event.field && event.field !== 'symbol') {
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
    if (event.field && event.field !== 'Left Symbol' && event.field !== 'Right Symbol') {
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
    this._selectedGlyphIndex$.next(event[1]);
  }

  get glyphsWithSymbols(): any[] {
    return this.resourceData?.definitions.map((g: any) => ({ ...g, symbol: this.getSymbol(g.code) })) || [];
  }

  get kerningsWithSymbols(): any[] {
    return (this.resourceData?.kernings || []).map((k: any) => ({
      ...k,
      'Left Symbol': this.getSymbol(k.left),
      'Right Symbol': this.getSymbol(k.right),
      'Left Symbol Code': k.left,
      'Right Symbol Code': k.right,
      Kerning: k.kerning,
      Unk: k.unk,
    }));
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
