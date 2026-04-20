import {
  AfterViewInit,
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  ElementRef,
  EventEmitter,
  Input,
  NgZone,
  OnDestroy,
  Output,
  ViewChild,
} from '@angular/core';
import { GuiComponentInterface } from '../../gui-component.interface';
import { BehaviorSubject, combineLatest, Subject, takeUntil } from 'rxjs';
import { Resource } from '../../types';
import { EelDelegateService } from '../../../../services/eel-delegate.service';
import { NavigationService } from '../../../../services/navigation.service';
import { MainService } from '../../../../services/main.service';
import * as PIXI from 'pixi.js';
import { Assets, BitmapFont, bitmapFontTextParser, BitmapText, Cache } from 'pixi.js';
import { ArrayTableColumn } from '../../common/data-table/data-table.component';
import { joinId } from '../../../../utils/join-id';

@Component({
  selector: 'app-font-block-ui',
  templateUrl: './font.block-ui.component.html',
  styleUrls: ['./font.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FontBlockUiComponent implements GuiComponentInterface, AfterViewInit, OnDestroy {
  @ViewChild('fullBitmapCanvas') fullBitmapCanvas!: ElementRef<HTMLCanvasElement>;
  @ViewChild('textPreviewContainer') textPreviewContainer!: ElementRef<HTMLDivElement>;

  _resource$: BehaviorSubject<Resource | null> = new BehaviorSubject<Resource | null>(null);
  _selectedGlyphIndex$: BehaviorSubject<number> = new BehaviorSubject<number>(0);
  _text$: BehaviorSubject<string> = new BehaviorSubject<string>('The quick brown fox jumps over the lazy dog\n0123456789\n!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~');

  _glyphColumns: ArrayTableColumn[] = [];
  _kerningColumns: ArrayTableColumn[] = [];

  @Input() set resource(value: Resource | null) {
    this._resource$.next(value);
    this.updateColumns(value);
  }

  get resource(): Resource | null {
    return this._resource$.getValue();
  }

  @Output('changed') changed: EventEmitter<void> = new EventEmitter<void>();

  private readonly destroyed$: Subject<void> = new Subject<void>();
  private _image: HTMLImageElement | null = null;
  private _pixiApp: PIXI.Application | null = null;
  private _bitmapText: BitmapText | null = null;
  private _fontId: string | null = null;
  private _resizeObserver: ResizeObserver | null = null;

  constructor(
    private readonly eelDelegate: EelDelegateService,
    public readonly navigation: NavigationService,
    public readonly main: MainService,
    private readonly ngZone: NgZone,
    private readonly cdr: ChangeDetectorRef,
  ) {
  }

  async ngAfterViewInit(): Promise<void> {
    this._pixiApp = new PIXI.Application();
    await this._pixiApp.init({
      background: '#000000',
    });
    this.textPreviewContainer.nativeElement.appendChild(this._pixiApp.canvas);

    combineLatest([this._resource$, this._selectedGlyphIndex$, this._text$])
      .pipe(takeUntil(this.destroyed$))
      .subscribe(([res, index, text]) => {
        this.render(res, index, text);
      });

    this._resizeObserver = new ResizeObserver(() => {
      this.ngZone.run(() => {
        const res = this.resource;
        const index = this._selectedGlyphIndex$.getValue();
        if (res) {
          this.renderFullBitmap(res, index);
          this.renderTextPreviewPIXI(res, this._text$.getValue(), '', ''); // Trigger PIXI resize
        }
      });
    });
    this._resizeObserver.observe(this.fullBitmapCanvas.nativeElement);
    this._resizeObserver.observe(this.textPreviewContainer.nativeElement);
  }

  private async render(res: Resource | null, index: number, text: string) {
    if (!res || !this.fullBitmapCanvas || !this._pixiApp) return;
    const paths = await this.eelDelegate.serializeResource(res.id);
    const imagePath = paths.find(x => x.endsWith('.png'));
    const fntPath = paths.find(x => x.endsWith('.fnt'));
    if (!imagePath) return;

    const finalImagePath = `${imagePath}?t=${new Date().getTime()}`;

    if (!this._image || this._image.src !== finalImagePath) {
      this._image = new Image();
      this._image.src = finalImagePath;
      await new Promise(resolve => (this._image!.onload = resolve));
    }

    let fntTextContent = '';
    try {
      const response = await fetch(fntPath!);
      fntTextContent = await response.text();
    } catch (e) {
      console.error('Failed to load .fnt file, falling back to resource data', e);
    }

    this.renderFullBitmap(res, index);
    await this.renderTextPreviewPIXI(res, text, fntTextContent, finalImagePath);
  }

  private renderFullBitmap(res: Resource, index: number) {
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

    const glyphs = res.data.definitions;
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
      else if (areaCanvasX + areaCanvasW > canvasWidth) offsetX -= (areaCanvasX + areaCanvasW - canvasWidth);

      if (areaCanvasY < 0) offsetY -= areaCanvasY;
      else if (areaCanvasY + areaCanvasH > canvasHeight) offsetY -= (areaCanvasY + areaCanvasH - canvasHeight);

      ctx.drawImage(this._image!, offsetX, offsetY, imgWidth * ratio, imgHeight * ratio);

      const glyphCanvasX = offsetX + glyph.x * ratio;
      const glyphCanvasY = offsetY + glyph.y * ratio;
      const glyphCanvasW = glyph.width * ratio;
      const glyphCanvasH = glyph.height * ratio;

      // Draw bounding box
      ctx.strokeStyle = 'red';
      ctx.lineWidth = 2;
      ctx.strokeRect(
        glyphCanvasX,
        glyphCanvasY,
        glyphCanvasW,
        glyphCanvasH,
      );

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

  private async renderTextPreviewPIXI(res: Resource, text: string, fntText: string, imagePath: string) {
    if (!this._pixiApp) return;

    const fontName = `Font_${res.id.replace(/\//g, '_')}`;

    if (imagePath && fntText && this._fontId !== fontName) {
      const texture = await Assets.load(imagePath);
      const bitmapFontData = bitmapFontTextParser.parse(fntText);
      bitmapFontData.fontFamily = fontName; // Ensure the parsed data has our unique font name
      const font = new BitmapFont({
        data: bitmapFontData,
        textures: [texture],
      });
      Cache.set(fontName, font);
      this._fontId = fontName;
    }

    if (!this._bitmapText) {
      this._bitmapText = new BitmapText({
        text: text,
        style: {
          fontFamily: fontName,
        },
      });
      this._pixiApp.stage.addChild(this._bitmapText);
    } else {
      this._bitmapText.text = text;
      if (this._fontId === fontName) {
        this._bitmapText.style.fontFamily = fontName;
      }
    }

    // Adjust canvas size to fit text if needed, or just let PIXI handle it with resizeTo
    // But we might want to manually set height based on text
    const bounds = this._bitmapText.getBounds();
    const containerWidth = this.textPreviewContainer.nativeElement.clientWidth;
    const targetHeight = Math.max(bounds.height + 40, 200, this.textPreviewContainer.nativeElement.clientHeight);
    if (this._pixiApp.renderer.width !== containerWidth || this._pixiApp.renderer.height !== targetHeight) {
      this._pixiApp.renderer.resize(containerWidth, targetHeight);
    }
  }

  private updateColumns(res: Resource | null) {
    if (!res) return;
    const glyphs = this.glyphs;
    if (glyphs.length > 0) {
      const gSchema = res.schema.fields.find((f: any) => f.name === 'definitions')?.schema;
      const gItemSchema = gSchema?.child_schema;
      if (gItemSchema) {
        this._glyphColumns = [
          { key: 'symbol', index: -1, readonly: true, schema: { block_class_mro: 'UTF8Block__' } },
          ...gItemSchema.fields.map((f: any, i: number) => ({ key: f.name, index: i, schema: f.schema })),
        ];
      }
    }

    const kernings = this.kernings;
    if (kernings.length > 0) {
      const kSchema = res.schema.fields.find((f: any) => f.name === 'kernings')?.schema;
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
    const newItem = await this.main.getNewItemData(joinId(this.resource!.id, 'definitions'));
    this.glyphs.push(newItem);
    this.main.dataBlockChange$.next([joinId(this.resource!.id, 'definitions'), this.glyphs]);
    this.cdr.markForCheck();
  }

  removeGlyph(index: number) {
    this.glyphs.splice(index, 1);
    this.main.dataBlockChange$.next([joinId(this.resource!.id, 'definitions'), this.glyphs]);
    this.cdr.markForCheck();
  }

  moveGlyphUp(index: number) {
    const temp = this.glyphs[index];
    this.glyphs[index] = this.glyphs[index - 1];
    this.glyphs[index - 1] = temp;
    this.main.dataBlockChange$.next([joinId(this.resource!.id, 'definitions'), this.glyphs]);
    this.cdr.markForCheck();
  }

  moveGlyphDown(index: number) {
    const temp = this.glyphs[index];
    this.glyphs[index] = this.glyphs[index + 1];
    this.glyphs[index + 1] = temp;
    this.main.dataBlockChange$.next([joinId(this.resource!.id, 'definitions'), this.glyphs]);
    this.cdr.markForCheck();
  }

  onGlyphDataChanged(event: { index: number; field: string | null; subField: string | null; value: any }) {
    const glyph = this.glyphs[event.index];
    if (glyph && event.field && event.field !== 'symbol') {
      glyph[event.field] = event.value;
      this.changed.emit();
      this._resource$.next({ ...this.resource! });
      this.cdr.markForCheck();
    }
  }

  async addKerning() {
    const newItem = await this.main.getNewItemData(joinId(this.resource!.id, 'kernings'));
    this.kernings.push(newItem);
    this.main.dataBlockChange$.next([joinId(this.resource!.id, 'kernings'), this.kernings]);
    this.cdr.markForCheck();
  }

  removeKerning(index: number) {
    this.kernings.splice(index, 1);
    this.main.dataBlockChange$.next([joinId(this.resource!.id, 'kernings'), this.kernings]);
    this.cdr.markForCheck();
  }

  moveKerningUp(index: number) {
    const temp = this.kernings[index];
    this.kernings[index] = this.kernings[index - 1];
    this.kernings[index - 1] = temp;
    this.main.dataBlockChange$.next([joinId(this.resource!.id, 'kernings'), this.kernings]);
    this.cdr.markForCheck();
  }

  moveKerningDown(index: number) {
    const temp = this.kernings[index];
    this.kernings[index] = this.kernings[index + 1];
    this.kernings[index + 1] = temp;
    this.main.dataBlockChange$.next([joinId(this.resource!.id, 'kernings'), this.kernings]);
    this.cdr.markForCheck();
  }

  onKerningDataChanged(event: { index: number; field: string | null; subField: string | null; value: any }) {
    const kerning = this.kernings[event.index];
    if (kerning && event.field && event.field !== 'Left Symbol' && event.field !== 'Right Symbol') {
      // Mapping back from DataTable display keys to data keys if necessary
      let dataField = event.field;
      if (dataField === 'Left Symbol Code') dataField = 'left';
      else if (dataField === 'Right Symbol Code') dataField = 'right';
      else if (dataField === 'Kerning') dataField = 'kerning';
      else if (dataField === 'Unk') dataField = 'unk';

      kerning[dataField] = event.value;
      this.changed.emit();
      this._resource$.next({ ...this.resource! });
      this.cdr.markForCheck();
    }
  }

  onGlyphFocused(event: [string[], number]) {
    this.selectGlyph(event[1]);
  }

  get glyphsWithSymbols(): any[] {
    return this.glyphs.map(g => ({ ...g, symbol: this.getSymbol(g.code) }));
  }

  get kerningsWithSymbols(): any[] {
    return (this.kernings || []).map(k => ({
      ...k,
      'Left Symbol': this.getSymbol(k.left),
      'Right Symbol': this.getSymbol(k.right),
      'Left Symbol Code': k.left,
      'Right Symbol Code': k.right,
      'Kerning': k.kerning,
      'Unk': k.unk,
    }));
  }

  onTextChange(event: Event) {
    this._text$.next((event.target as HTMLTextAreaElement).value);
  }

  selectGlyph(index: number) {
    this._selectedGlyphIndex$.next(index);
  }

  onNavigateToBitmap() {
    if (this.resource) {
      this.navigation.navigateToId(this.resource.id + '/bitmap');
    }
  }

  get glyphs(): any[] {
    return this.resource?.data?.definitions;
  }

  get glyphKeys(): string[] {
    const glyphs = this.glyphs;
    if (glyphs.length === 0) return [];
    return ['symbol', ...Object.keys(glyphs[0]).filter(k => k !== 'num_kern' && k !== 'kern_index')];
  }

  get kernings(): any[] {
    return this.resource?.data?.kernings;
  }

  get kerningKeys(): string[] {
    return ['Left Symbol', 'Right Symbol', 'Left Symbol Code', 'Right Symbol Code', 'Kerning', 'Unk'];
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

  onCellChange(index: number, key: string, event: any) {
    const value = event.target.value;
    const glyph = this.glyphs[index];
    if (glyph) {
      glyph[key] = parseInt(value, 10);
      this.changed.emit();
      this._resource$.next({ ...this.resource! });
    }
  }

  onKerningCellChange(index: number, key: string, event: any) {
    const value = event.target.value;
    const kerning = this.kernings[index];
    if (kerning) {
      let fieldKey = '';
      if (key === 'Left Symbol Code') fieldKey = 'left';
      else if (key === 'Right Symbol Code') fieldKey = 'right';
      else if (key === 'Kerning') fieldKey = 'kerning';
      else if (key === 'Unk') fieldKey = 'unk';

      if (fieldKey) {
        kerning[fieldKey] = parseInt(value, 10);
        this.changed.emit();
        // Since we modified the array directly, and we want to trigger change detection
        this._resource$.next({ ...this.resource! });
      }
    }
  }

  ngOnDestroy(): void {
    this.destroyed$.next();
    this.destroyed$.complete();
    if (this._resizeObserver) {
      this._resizeObserver.disconnect();
    }
  }
}
