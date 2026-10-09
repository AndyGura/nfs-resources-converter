import {
  AfterViewInit,
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  ElementRef,
  EventEmitter,
  HostListener,
  Input,
  NgZone,
  OnDestroy,
  OnInit,
  Output,
  ViewChild,
} from '@angular/core';
import {
  applyDrawStroke,
  applyFalloffDrag,
  applySmoothBrush,
  CurvePoint,
  decimalsForStep,
  formatValue,
  nearestIndexByX,
  NiceScale,
  niceScale,
  snapValue,
  ValueConstraints,
} from './curve-editor.utils';

export type { CurvePoint } from './curve-editor.utils';

export type CurveSeries = {
  id: string;
  label: string;
  color: string;
  points: CurvePoint[];
  // y axis the series is drawn against
  axis?: 'left' | 'right';
  style?: 'line' | 'step' | 'bars' | 'points';
  // which coordinates of a point the user can drag
  editable?: 'none' | 'x' | 'y' | 'xy';
  // points from this index on are not used by the game: drawn faded, never edited, left out of the axis range
  activeCount?: number;
  lockedIndices?: number[];
  x?: ValueConstraints;
  y?: ValueConstraints;
  // moves a dragged point where it may be, e.g. along a line. Called after the constraints are applied
  constrain?: (index: number, p: CurvePoint) => CurvePoint;
  // tooltip / selection names of the points (gear names...)
  pointLabels?: string[];
  formatY?: (y: number) => string;
  dashed?: boolean;
  strokeWidth?: number;
  hideInLegend?: boolean;
  // false hides the series from the tooltip
  inTooltip?: boolean;
};

export type CurveMarker = {
  id: string;
  value: number;
  orientation?: 'vertical' | 'horizontal';
  // for horizontal markers: the y axis of the value
  axis?: 'left' | 'right';
  label: string;
  color: string;
  editable?: boolean;
  constraints?: ValueConstraints;
  format?: (v: number) => string;
};

export type CurveAxis = {
  label: string;
  min?: number;
  max?: number;
  format?: (v: number) => string;
  // x axis only: names of the integer positions 0, 1, 2... (bar charts)
  categories?: string[];
};

export type CurveSeriesChange = { seriesId: string; points: CurvePoint[]; changed: number[] };
export type CurveMarkerChange = { markerId: string; value: number };
export type CurveTool = 'drag' | 'draw' | 'smooth';

type Scale = NiceScale & { px0: number; px1: number };

type Interaction =
  | {
      kind: 'point';
      seriesId: string;
      index: number;
      start: CurvePoint;
      original: CurvePoint[];
      working: CurvePoint[];
      changed: Set<number>;
    }
  | {
      kind: 'draw' | 'smooth';
      seriesId: string;
      last: CurvePoint;
      working: CurvePoint[];
      changed: Set<number>;
    }
  | { kind: 'marker'; markerId: string; value: number; original: number }
  | { kind: 'pan'; startPx: number; domain: [number, number] };

type SeriesVm = {
  id: string;
  color: string;
  dashed: boolean;
  width: number;
  isActive: boolean;
  activePath: string;
  inactivePath: string;
  bars: { x: number; y: number; w: number; h: number; inactive: boolean }[];
  handles: { cx: number; cy: number; index: number }[];
};

type MarkerVm = {
  id: string;
  color: string;
  label: string;
  editable: boolean;
  vertical: boolean;
  pos: number;
  // vertical markers: label position, staggered so close markers do not overlap
  labelX: number;
  labelY: number;
  labelAnchor: 'start' | 'end';
};

type TooltipVm = {
  left: number;
  top: number;
  flip: boolean;
  title: string;
  rows: { color: string; label: string; value: string }[];
};

const MARGIN_TOP = 22;
const MARGIN_BOTTOM = 40;
const MARGIN_LEFT = 60;
const MARGIN_RIGHT_SINGLE = 16;
const MARGIN_RIGHT_DOUBLE = 60;
const HIT_RADIUS_PX = 12;
const DENSE_POINTS = 24;
const MAX_HANDLES = 80;
const PX_LIMIT = 1e5;

// Interactive SVG chart of one or more series, with draggable points and markers. Every finished gesture (drag,
// stroke, nudge, typed value) is emitted once, so the host can turn it into one undoable change
@Component({
  selector: 'app-curve-editor',
  templateUrl: './curve-editor.component.html',
  styleUrls: ['./curve-editor.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  standalone: false,
  host: { tabindex: '0' },
})
export class CurveEditorComponent implements OnInit, AfterViewInit, OnDestroy {
  private _series: CurveSeries[] = [];
  @Input()
  set series(value: CurveSeries[] | null | undefined) {
    const old = new Map(this._series.map(s => [s.id, s.points]));
    this._series = value || [];
    for (const s of this._series) {
      if (old.get(s.id) !== s.points) this.overrides.delete(s.id);
    }
    if (!this.editableSeries.some(s => s.id === this.activeSeriesId)) {
      this.activeSeriesId = this.editableSeries[0]?.id ?? null;
    }
    if (this.selected && !this._series.some(s => s.id === this.selected!.seriesId)) {
      this.selected = null;
    }
    this.render();
  }
  get series(): CurveSeries[] {
    return this._series;
  }

  private _markers: CurveMarker[] = [];
  @Input()
  set markers(value: CurveMarker[] | null | undefined) {
    this._markers = value || [];
    this.render();
  }
  get markers(): CurveMarker[] {
    return this._markers;
  }

  private _xAxis: CurveAxis = { label: '' };
  @Input()
  set xAxis(value: CurveAxis) {
    this._xAxis = value || { label: '' };
    this.render();
  }
  get xAxis(): CurveAxis {
    return this._xAxis;
  }

  private _yAxis: CurveAxis = { label: '' };
  @Input()
  set yAxis(value: CurveAxis) {
    this._yAxis = value || { label: '' };
    this.render();
  }
  get yAxis(): CurveAxis {
    return this._yAxis;
  }

  private _y2Axis: CurveAxis | null = null;
  @Input()
  set y2Axis(value: CurveAxis | null | undefined) {
    this._y2Axis = value || null;
    this.render();
  }
  get y2Axis(): CurveAxis | null {
    return this._y2Axis;
  }

  @Input() title: string = '';
  @Input() hint: string = '';
  @Input() height: number = 280;

  private _disabled = false;
  @Input()
  set disabled(value: boolean | null | undefined) {
    this._disabled = !!value;
    this.render();
  }
  get disabled(): boolean {
    return this._disabled;
  }

  // tooltip title for the x under the cursor; defaults to the x axis format
  @Input() describeX?: (x: number) => string;

  @Output() seriesChange = new EventEmitter<CurveSeriesChange>();
  // live points while a gesture is in progress, for hosts that redraw derived curves along
  @Output() seriesPreview = new EventEmitter<CurveSeriesChange>();
  @Output() markerChange = new EventEmitter<CurveMarkerChange>();
  @Output() markerPreview = new EventEmitter<CurveMarkerChange>();

  @ViewChild('svg', { static: true }) svgRef!: ElementRef<SVGSVGElement>;

  width = 600;
  tool: CurveTool = 'drag';
  radius = 0;
  activeSeriesId: string | null = null;
  hidden = new Set<string>();
  selected: { seriesId: string; index: number } | null = null;
  zoom: [number, number] | null = null;
  readonly clipId = 'curve-clip-' + Math.random().toString(36).substring(2, 10);

  // view model
  plot = { left: MARGIN_LEFT, top: MARGIN_TOP, right: 0, bottom: 0, width: 0, height: 0 };
  xTicks: { pos: number; label: string }[] = [];
  yTicks: { pos: number; label: string }[] = [];
  y2Ticks: { pos: number; label: string }[] = [];
  seriesVm: SeriesVm[] = [];
  markersVm: MarkerVm[] = [];
  tooltip: TooltipVm | null = null;
  crosshairX: number | null = null;
  hoverHandle: { cx: number; cy: number; color: string } | null = null;
  selectedHandle: { cx: number; cy: number; color: string } | null = null;

  private xScale!: Scale;
  private yScale!: Scale;
  private y2Scale!: Scale;
  // axis ranges stay put during a gesture, so the curve does not slide away under the cursor
  private frozen: { y: Scale; y2: Scale } | null = null;
  private interaction: Interaction | null = null;
  private overrides = new Map<string, CurvePoint[]>();
  private overrideTimer: any;
  private hoverPx: { x: number; y: number } | null = null;
  private resizeObserver?: ResizeObserver;
  private initialized = false;

  constructor(
    private readonly cdr: ChangeDetectorRef,
    private readonly host: ElementRef<HTMLElement>,
    private readonly zone: NgZone,
  ) {}

  ngOnInit(): void {
    this.initialized = true;
    this.render();
  }

  ngAfterViewInit(): void {
    this.resizeObserver = new ResizeObserver(entries => {
      const w = Math.floor(entries[0].contentRect.width);
      if (w > 0 && w !== this.width) {
        this.zone.run(() => {
          this.width = w;
          this.render();
        });
      }
    });
    this.resizeObserver.observe(this.svgRef.nativeElement.parentElement!);
  }

  ngOnDestroy(): void {
    this.resizeObserver?.disconnect();
    clearTimeout(this.overrideTimer);
  }

  get editableSeries(): CurveSeries[] {
    return this._series.filter(s => s.editable && s.editable !== 'none');
  }

  get activeSeries(): CurveSeries | null {
    return this._series.find(s => s.id === this.activeSeriesId) || null;
  }

  get isEditable(): boolean {
    return !this.disabled && this.editableSeries.length > 0;
  }

  // the brushes work on dense y-only curves (tables of values), not on a few free points
  get brushesAvailable(): boolean {
    const s = this.activeSeries;
    return !!s && s.editable === 'y' && !s.constrain && this.activeCount(s) > DENSE_POINTS;
  }

  get legend(): CurveSeries[] {
    return this._series.filter(s => !s.hideInLegend);
  }

  get selectedInfo(): {
    series: CurveSeries;
    index: number;
    label: string;
    x: string;
    y: number;
    xValue: number;
    canX: boolean;
    canY: boolean;
  } | null {
    if (!this.selected) return null;
    const s = this._series.find(x => x.id === this.selected!.seriesId);
    const p = s && this.pointsOf(s)[this.selected.index];
    if (!s || !p) return null;
    return {
      series: s,
      index: this.selected.index,
      label: s.pointLabels?.[this.selected.index] ?? '#' + this.selected.index,
      x: this.formatX(p.x),
      y: this.roundForInput(p.y, s.y?.step),
      xValue: this.roundForInput(p.x, s.x?.step),
      canX: !this.disabled && (s.editable === 'x' || s.editable === 'xy'),
      canY: !this.disabled && (s.editable === 'y' || s.editable === 'xy'),
    };
  }

  setTool(tool: CurveTool) {
    this.tool = tool;
    if (tool !== 'drag' && this.radius < 2) this.radius = 4;
    this.cdr.markForCheck();
  }

  onLegendClick(s: CurveSeries) {
    if (s.editable && s.editable !== 'none' && !this.disabled && s.id !== this.activeSeriesId) {
      this.activeSeriesId = s.id;
      this.hidden.delete(s.id);
      this.selected = null;
      if (!this.brushesAvailable) this.tool = 'drag';
    } else if (s.id !== this.activeSeriesId) {
      this.toggleVisibility(s);
      return;
    }
    this.render();
  }

  toggleVisibility(s: CurveSeries, event?: Event) {
    event?.stopPropagation();
    if (this.hidden.has(s.id)) this.hidden.delete(s.id);
    else this.hidden.add(s.id);
    if (this.selected?.seriesId === s.id) this.selected = null;
    this.render();
  }

  resetZoom() {
    this.zoom = null;
    this.render();
  }

  // ---------- geometry ----------

  private activeCount(s: CurveSeries): number {
    return Math.min(s.activeCount ?? s.points.length, this.pointsOf(s).length);
  }

  private pointsOf(s: CurveSeries): CurvePoint[] {
    const i = this.interaction;
    if (i && (i.kind === 'point' || i.kind === 'draw' || i.kind === 'smooth') && i.seriesId === s.id) {
      return i.working;
    }
    return this.overrides.get(s.id) || s.points;
  }

  private markerValue(m: CurveMarker): number {
    const i = this.interaction;
    return i && i.kind === 'marker' && i.markerId === m.id ? i.value : m.value;
  }

  private isLocked(s: CurveSeries, index: number): boolean {
    return index >= this.activeCount(s) || !!s.lockedIndices?.includes(index);
  }

  private visibleSeries(): CurveSeries[] {
    return this._series.filter(s => !this.hidden.has(s.id));
  }

  private computeScales() {
    const plotW = Math.max(40, this.width - MARGIN_LEFT - (this.y2Axis ? MARGIN_RIGHT_DOUBLE : MARGIN_RIGHT_SINGLE));
    const plotH = Math.max(40, this.height - MARGIN_TOP - MARGIN_BOTTOM);
    this.plot = {
      left: MARGIN_LEFT,
      top: MARGIN_TOP,
      width: plotW,
      height: plotH,
      right: MARGIN_LEFT + plotW,
      bottom: MARGIN_TOP + plotH,
    };
    const visible = this.visibleSeries();
    const hasBars = visible.some(s => s.style === 'bars');

    // x
    let xs: number[] = [];
    for (const s of visible) {
      const pts = this.pointsOf(s);
      for (let i = 0; i < this.activeCount(s); i++) xs.push(pts[i].x);
    }
    for (const m of this._markers) if (m.orientation !== 'horizontal') xs.push(this.markerValue(m));
    xs = xs.filter(isFinite);
    let xMin = this.xAxis.min ?? (xs.length ? Math.min(...xs) : 0);
    let xMax = this.xAxis.max ?? (xs.length ? Math.max(...xs) : 1);
    let xNice: NiceScale;
    if (this.xAxis.categories || hasBars) {
      const n = this.xAxis.categories?.length ?? Math.round(xMax) + 1;
      xNice = { min: -0.5, max: n - 0.5, step: 1, ticks: Array.from({ length: n }, (_, i) => i) };
    } else {
      xNice = niceScale(xMin, xMax, Math.max(3, Math.round(plotW / 90)));
      if (this.xAxis.min !== undefined) xNice.min = this.xAxis.min;
      if (this.xAxis.max !== undefined) xNice.max = this.xAxis.max;
      xNice.ticks = xNice.ticks.filter(t => t >= xNice.min - 1e-9 && t <= xNice.max + 1e-9);
    }
    if (this.zoom) {
      const z = niceScale(this.zoom[0], this.zoom[1], Math.max(3, Math.round(plotW / 90)));
      xNice = { ...z, min: this.zoom[0], max: this.zoom[1] };
      xNice.ticks = z.ticks.filter(t => t >= this.zoom![0] - 1e-9 && t <= this.zoom![1] + 1e-9);
    }
    this.xScale = { ...xNice, px0: this.plot.left, px1: this.plot.right };

    if (this.frozen) {
      this.yScale = this.frozen.y;
      this.y2Scale = this.frozen.y2;
      return;
    }
    const yFor = (axis: 'left' | 'right', conf: CurveAxis | null): Scale => {
      let ys: number[] = [];
      let editable = false;
      for (const s of visible) {
        if ((s.axis ?? 'left') !== axis) continue;
        editable ||= !!s.editable && s.editable !== 'none';
        const pts = this.pointsOf(s);
        const count = this.activeCount(s);
        for (let i = 0; i < count; i++) {
          if (this.zoom && s.style !== 'bars' && (pts[i].x < this.zoom[0] || pts[i].x > this.zoom[1])) continue;
          ys.push(pts[i].y);
        }
        if (s.style === 'bars') ys.push(0);
      }
      for (const m of this._markers) {
        if (m.orientation === 'horizontal' && (m.axis ?? 'left') === axis) ys.push(this.markerValue(m));
      }
      ys = ys.filter(isFinite);
      let min = conf?.min ?? (ys.length ? Math.min(...ys) : 0);
      let max = conf?.max ?? (ys.length ? Math.max(...ys) : 1);
      // room to drag above the highest point
      if (editable && conf?.max === undefined) max += (max - min || Math.abs(max) || 1) * 0.08;
      const nice = niceScale(min, max, Math.max(3, Math.round(plotH / 50)));
      if (conf?.min !== undefined) nice.min = conf.min;
      if (conf?.max !== undefined) nice.max = conf.max;
      nice.ticks = nice.ticks.filter(t => t >= nice.min - 1e-9 && t <= nice.max + 1e-9);
      return { ...nice, px0: this.plot.bottom, px1: this.plot.top };
    };
    this.yScale = yFor('left', this.yAxis);
    this.y2Scale = yFor('right', this.y2Axis);
  }

  private toPx(scale: Scale, v: number): number {
    const t = (v - scale.min) / (scale.max - scale.min || 1);
    const px = scale.px0 + t * (scale.px1 - scale.px0);
    return Math.max(-PX_LIMIT, Math.min(PX_LIMIT, px));
  }

  private fromPx(scale: Scale, px: number): number {
    const t = (px - scale.px0) / (scale.px1 - scale.px0 || 1);
    return scale.min + t * (scale.max - scale.min);
  }

  private yScaleOf(s: CurveSeries): Scale {
    return (s.axis ?? 'left') === 'right' ? this.y2Scale : this.yScale;
  }

  private barWidth(): number {
    return Math.max(
      4,
      Math.min(48, ((this.plot.width / (this.xScale.max - this.xScale.min)) * 0.6) / this.barGroupSize()),
    );
  }

  private barGroupSize(): number {
    return Math.max(1, this.visibleSeries().filter(s => s.style === 'bars').length);
  }

  private barOffset(s: CurveSeries): number {
    const bars = this.visibleSeries().filter(x => x.style === 'bars');
    const i = bars.indexOf(s);
    return (i - (bars.length - 1) / 2) * this.barWidth();
  }

  private pointPx(s: CurveSeries, p: CurvePoint): { x: number; y: number } {
    const x = this.toPx(this.xScale, p.x) + (s.style === 'bars' ? this.barOffset(s) : 0);
    return { x, y: this.toPx(this.yScaleOf(s), p.y) };
  }

  formatX(x: number): string {
    if (this.xAxis.categories) return this.xAxis.categories[Math.round(x)] ?? '' + x;
    if (this.xAxis.format) return this.xAxis.format(x);
    return formatValue(x, decimalsForStep(this.xScale ? this.xScale.step / 10 : undefined));
  }

  formatY(s: CurveSeries, y: number): string {
    if (s.formatY) return s.formatY(y);
    const axis = (s.axis ?? 'left') === 'right' ? this.y2Axis : this.yAxis;
    if (axis?.format) return axis.format(y);
    const scale = this.yScaleOf(s);
    return formatValue(y, decimalsForStep(s.y?.step ?? (scale ? scale.step / 100 : undefined)));
  }

  // ---------- rendering ----------

  render() {
    if (!this.initialized) return;
    this.computeScales();
    const tickLabel = (axis: CurveAxis | null, scale: Scale, v: number) =>
      axis?.format ? axis.format(v) : formatValue(v, decimalsForStep(scale.step));
    this.xTicks = this.xScale.ticks.map(t => ({
      pos: this.toPx(this.xScale, t),
      label: this.xAxis.categories ? (this.xAxis.categories[t] ?? '') : tickLabel(this.xAxis, this.xScale, t),
    }));
    this.yTicks = this.yScale.ticks.map(t => ({
      pos: this.toPx(this.yScale, t),
      label: tickLabel(this.yAxis, this.yScale, t),
    }));
    this.y2Ticks = this.y2Axis
      ? this.y2Scale.ticks.map(t => ({
          pos: this.toPx(this.y2Scale, t),
          label: tickLabel(this.y2Axis, this.y2Scale, t),
        }))
      : [];

    this.seriesVm = [];
    for (const s of this.visibleSeries()) {
      const pts = this.pointsOf(s);
      const count = this.activeCount(s);
      const isActive = s.id === this.activeSeriesId && this.isEditable;
      const vm: SeriesVm = {
        id: s.id,
        color: s.color,
        dashed: !!s.dashed,
        width: s.strokeWidth ?? (isActive ? 2.25 : 1.75),
        isActive,
        activePath: '',
        inactivePath: '',
        bars: [],
        handles: [],
      };
      if (s.style === 'bars') {
        const w = this.barWidth();
        const base = this.toPx(this.yScaleOf(s), 0);
        pts.forEach((p, i) => {
          const { x, y } = this.pointPx(s, p);
          vm.bars.push({ x: x - w / 2, y: Math.min(y, base), w, h: Math.abs(base - y), inactive: i >= count });
        });
      } else if (s.style !== 'points') {
        vm.activePath = this.buildPath(s, pts.slice(0, count));
        if (count < pts.length) vm.inactivePath = this.buildPath(s, pts.slice(Math.max(0, count - 1)));
      }
      const editable = this.isEditable && !!s.editable && s.editable !== 'none';
      if (editable || s.style === 'points') {
        const handles: { cx: number; cy: number; index: number }[] = [];
        for (let i = 0; i < count; i++) {
          if (this.zoomedOut(pts[i].x)) continue;
          const { x, y } = this.pointPx(s, pts[i]);
          handles.push({ cx: x, cy: s.style === 'bars' ? y : y, index: i });
        }
        if (s.style === 'points' || (handles.length <= MAX_HANDLES && (isActive || count <= DENSE_POINTS))) {
          vm.handles = handles.filter(h => !s.lockedIndices?.includes(h.index) || s.style === 'points');
        }
      }
      this.seriesVm.push(vm);
    }
    // the edited series on top
    this.seriesVm.sort((a, b) => +a.isActive - +b.isActive);

    this.markersVm = this._markers
      .map(m => {
        const vertical = m.orientation !== 'horizontal';
        const v = this.markerValue(m);
        const pos = vertical
          ? this.toPx(this.xScale, v)
          : this.toPx((m.axis ?? 'left') === 'right' ? this.y2Scale : this.yScale, v);
        return {
          id: m.id,
          color: m.color,
          label: m.label + ': ' + (m.format ? m.format(v) : formatValue(v, decimalsForStep(m.constraints?.step))),
          editable: !!m.editable && !this.disabled,
          vertical,
          pos,
          labelX: 0,
          labelY: 0,
          labelAnchor: 'start' as 'start' | 'end',
        };
      })
      .filter(m =>
        m.vertical
          ? m.pos >= this.plot.left - 0.5 && m.pos <= this.plot.right + 0.5
          : m.pos >= this.plot.top - 0.5 && m.pos <= this.plot.bottom + 0.5,
      );
    this.layoutMarkerLabels();

    this.selectedHandle = null;
    if (this.selected) {
      const s = this._series.find(x => x.id === this.selected!.seriesId);
      const p = s && this.pointsOf(s)[this.selected.index];
      if (s && p && !this.hidden.has(s.id)) {
        const { x, y } = this.pointPx(s, p);
        this.selectedHandle = { cx: x, cy: y, color: s.color };
      }
    }
    this.updateHover();
    this.cdr.markForCheck();
  }

  // first row above the plot, the next ones inside its top edge
  private layoutMarkerLabels() {
    const rowsEnd: number[] = [];
    const vertical = this.markersVm.filter(m => m.vertical).sort((a, b) => a.pos - b.pos);
    for (const m of vertical) {
      const width = m.label.length * 6.2 + 8;
      const end = m.pos > this.plot.left + this.plot.width * 0.75;
      m.labelAnchor = end ? 'end' : 'start';
      m.labelX = m.pos + (end ? -7 : 7);
      const from = end ? m.labelX - width : m.labelX;
      let row = rowsEnd.findIndex(e => e < from);
      if (row < 0) {
        row = rowsEnd.length;
        rowsEnd.push(0);
      }
      rowsEnd[row] = from + width;
      m.labelY = row === 0 ? this.plot.top - 6 : this.plot.top + 4 + row * 13;
    }
  }

  private zoomedOut(x: number): boolean {
    return x < this.xScale.min || x > this.xScale.max;
  }

  private buildPath(s: CurveSeries, pts: CurvePoint[]): string {
    let d = '';
    let prev: { x: number; y: number } | null = null;
    for (const p of pts) {
      if (!isFinite(p.x) || !isFinite(p.y)) {
        prev = null;
        continue;
      }
      const c = this.pointPx(s, p);
      if (!prev) d += `M${c.x.toFixed(1)},${c.y.toFixed(1)}`;
      else if (s.style === 'step') d += `H${c.x.toFixed(1)}V${c.y.toFixed(1)}`;
      else d += `L${c.x.toFixed(1)},${c.y.toFixed(1)}`;
      prev = c;
    }
    return d;
  }

  private updateHover() {
    this.tooltip = null;
    this.crosshairX = null;
    this.hoverHandle = null;
    const h = this.hoverPx;
    if (!h || h.x < this.plot.left || h.x > this.plot.right || h.y < this.plot.top || h.y > this.plot.bottom) return;
    const x = this.fromPx(this.xScale, h.x);
    const rows: TooltipVm['rows'] = [];
    let snapX: number | null = null;
    for (const s of this.visibleSeries()) {
      if (s.inTooltip === false) continue;
      const pts = this.pointsOf(s);
      const count = this.activeCount(s);
      if (!count) continue;
      let idx: number;
      if (s.style === 'bars' || this.xAxis.categories) {
        idx = pts.findIndex(p => Math.round(p.x) === Math.round(x));
        if (idx < 0 || idx >= count) continue;
      } else if (pts.length <= 3 && s.style !== 'points') {
        // sparse lines (a gear from 0 to the redline): read the line at the cursor
        const y = this.interpolate(pts.slice(0, count), x);
        if (y === null) continue;
        rows.push({ color: s.color, label: s.label, value: this.formatY(s, y) });
        continue;
      } else {
        idx = nearestIndexByX(pts, x, count);
        if (s.style === 'points' && Math.abs(this.pointPx(s, pts[idx]).x - h.x) > HIT_RADIUS_PX) continue;
      }
      const p = pts[idx];
      const label = s.pointLabels?.[idx] ? `${s.label} (${s.pointLabels[idx]})` : s.label;
      rows.push({ color: s.color, label, value: this.formatY(s, p.y) });
      if (s.style !== 'points' && (s.id === this.activeSeriesId || snapX === null)) snapX = p.x;
    }
    if (!rows.length && !this.markersVm.length) return;
    const titleX = this.xAxis.categories ? Math.round(x) : (snapX ?? x);
    this.crosshairX = snapX !== null ? this.toPx(this.xScale, snapX) : h.x;
    const flip = h.x > this.plot.left + this.plot.width * 0.6;
    this.tooltip = {
      left: flip ? h.x - 12 : h.x + 12,
      top: Math.max(this.plot.top, Math.min(h.y - 10, this.plot.bottom - 40 - rows.length * 18)),
      flip,
      title: this.describeX ? this.describeX(titleX) : this.formatX(titleX),
      rows,
    };
    if (this.isEditable && !this.interaction && (this.tool === 'drag' || !this.brushesAvailable)) {
      const hit = this.hitPoint(h.x, h.y);
      if (hit) {
        const c = this.pointPx(hit.series, this.pointsOf(hit.series)[hit.index]);
        this.hoverHandle = { cx: c.x, cy: c.y, color: hit.series.color };
      }
    }
  }

  private interpolate(pts: CurvePoint[], x: number): number | null {
    for (let i = 0; i + 1 < pts.length; i++) {
      const a = pts[i];
      const b = pts[i + 1];
      if ((x >= a.x && x <= b.x) || (x >= b.x && x <= a.x)) {
        return Math.abs(b.x - a.x) < 1e-12 ? a.y : a.y + ((b.y - a.y) * (x - a.x)) / (b.x - a.x);
      }
    }
    return null;
  }

  // ---------- interaction ----------

  private eventPx(e: { clientX: number; clientY: number }): { x: number; y: number } {
    const r = this.svgRef.nativeElement.getBoundingClientRect();
    return { x: e.clientX - r.left, y: e.clientY - r.top };
  }

  // nearest editable point under (px, py) of all visible editable series; the edited series wins close calls
  private hitPoint(px: number, py: number): { series: CurveSeries; index: number } | null {
    let best: { series: CurveSeries; index: number } | null = null;
    let bestD = Infinity;
    for (const s of this.editableSeries) {
      if (this.hidden.has(s.id)) continue;
      const hit = this.hitSeriesPoint(s, px, py);
      if (!hit) continue;
      const d = hit.distance - (s.id === this.activeSeriesId ? 2 : 0);
      if (d < bestD) {
        bestD = d;
        best = { series: s, index: hit.index };
      }
    }
    return best;
  }

  private hitSeriesPoint(s: CurveSeries, px: number, py: number): { index: number; distance: number } | null {
    const pts = this.pointsOf(s);
    const count = this.activeCount(s);
    let best: number | null = null;
    let bestD = HIT_RADIUS_PX;
    if (s.style === 'bars') {
      const w = this.barWidth();
      for (let i = 0; i < count; i++) {
        if (this.isLocked(s, i)) continue;
        const c = this.pointPx(s, pts[i]);
        if (Math.abs(px - c.x) <= w / 2 + 2) return { index: i, distance: 0 };
      }
      return null;
    }
    const near = nearestIndexByX(pts, this.fromPx(this.xScale, px), count);
    // a few neighbours around the nearest x cover dense curves; sparse ones are checked in full
    const from = count > DENSE_POINTS ? Math.max(0, near - 12) : 0;
    const to = count > DENSE_POINTS ? Math.min(count - 1, near + 12) : count - 1;
    for (let i = from; i <= to; i++) {
      if (this.isLocked(s, i) || !isFinite(pts[i].x) || !isFinite(pts[i].y)) continue;
      const c = this.pointPx(s, pts[i]);
      const d = Math.hypot(c.x - px, c.y - py);
      if (d <= bestD) {
        bestD = d;
        best = i;
      }
    }
    return best === null ? null : { index: best, distance: bestD };
  }

  private hitMarker(px: number, py: number): CurveMarker | null {
    for (const vm of this.markersVm) {
      if (!vm.editable) continue;
      if (vm.vertical ? Math.abs(px - vm.pos) <= 6 : Math.abs(py - vm.pos) <= 6) {
        return this._markers.find(m => m.id === vm.id) || null;
      }
    }
    return null;
  }

  onPointerDown(e: PointerEvent) {
    if (e.button !== 0) return;
    const { x, y } = this.eventPx(e);
    this.host.nativeElement.focus({ preventScroll: true });
    // points first: an editable marker often runs through them (gear lines ending on the redline)
    const pointMode = this.tool === 'drag' || !this.brushesAvailable;
    const hit = this.isEditable && pointMode ? this.hitPoint(x, y) : null;
    const marker = hit ? null : this.hitMarker(x, y);
    if (marker) {
      this.interaction = { kind: 'marker', markerId: marker.id, value: marker.value, original: marker.value };
      this.capture(e);
      return;
    }
    const active = this.activeSeries;
    if (this.isEditable && active) {
      if (pointMode) {
        if (hit) {
          const { index } = hit;
          const s = hit.series;
          this.activeSeriesId = s.id;
          const pts = this.pointsOf(s);
          this.selected = { seriesId: s.id, index };
          this.frozen = { y: this.yScale, y2: this.y2Scale };
          this.interaction = {
            kind: 'point',
            seriesId: s.id,
            index,
            start: { x: this.fromPx(this.xScale, x), y: this.fromPx(this.yScaleOf(s), y) },
            original: pts.map(p => ({ ...p })),
            working: pts.map(p => ({ ...p })),
            changed: new Set(),
          };
          this.capture(e);
          this.render();
          return;
        }
      } else if (!this.hidden.has(active.id)) {
        const s = active;
        const pts = this.pointsOf(s);
        const p = { x: this.fromPx(this.xScale, x), y: this.fromPx(this.yScaleOf(s), y) };
        this.frozen = { y: this.yScale, y2: this.y2Scale };
        this.interaction = {
          kind: this.tool as 'draw' | 'smooth',
          seriesId: s.id,
          last: p,
          working: pts.map(q => ({ ...q })),
          changed: new Set(),
        };
        this.applyBrush(p);
        this.capture(e);
        return;
      }
    }
    if (this.selected) {
      this.selected = null;
      this.render();
    }
    if (this.zoom) {
      this.interaction = { kind: 'pan', startPx: x, domain: [...this.zoom] };
      this.capture(e);
    }
  }

  private capture(e: PointerEvent) {
    (e.target as Element).setPointerCapture?.(e.pointerId);
    e.preventDefault();
  }

  onPointerMove(e: PointerEvent) {
    const { x, y } = this.eventPx(e);
    this.hoverPx = { x, y };
    const it = this.interaction;
    if (!it) {
      this.render();
      return;
    }
    if (it.kind === 'marker') {
      const m = this._markers.find(q => q.id === it.markerId)!;
      const scale =
        m.orientation === 'horizontal' ? ((m.axis ?? 'left') === 'right' ? this.y2Scale : this.yScale) : this.xScale;
      it.value = snapValue(this.fromPx(scale, m.orientation === 'horizontal' ? y : x), m.constraints);
      this.markerPreview.emit({ markerId: m.id, value: it.value });
    } else if (it.kind === 'pan') {
      const span = it.domain[1] - it.domain[0];
      const shift = ((x - it.startPx) / this.plot.width) * span;
      this.zoom = this.clampZoom(it.domain[0] - shift, it.domain[1] - shift);
    } else if (it.kind === 'point') {
      const s = this._series.find(q => q.id === it.seriesId)!;
      const cur = { x: this.fromPx(this.xScale, x), y: this.fromPx(this.yScaleOf(s), y) };
      const dx = cur.x - it.start.x;
      const dy = cur.y - it.start.y;
      const canX = s.editable === 'x' || s.editable === 'xy';
      const canY = s.editable === 'y' || s.editable === 'xy';
      if (dy === 0 && dx === 0) {
        it.working = it.original.map(q => ({ ...q }));
        it.changed = new Set();
      } else if (canY && !canX && !s.constrain && this.radius > 0) {
        const r = applyFalloffDrag(it.original, it.index, dy, Math.round(this.radius), this.activeCount(s), s.y);
        it.working = r.points;
        it.changed = new Set(r.changed);
      } else {
        const o = it.original[it.index];
        // an axis that did not move keeps its value as it is, even off the snapping grid
        let p: CurvePoint = {
          x: canX && dx !== 0 ? snapValue(o.x + dx, s.x) : o.x,
          y: canY && dy !== 0 ? snapValue(o.y + dy, s.y) : o.y,
        };
        if (s.constrain) p = s.constrain(it.index, p);
        it.working = it.original.map(q => ({ ...q }));
        it.working[it.index] = p;
        it.changed = new Set(p.x !== o.x || p.y !== o.y ? [it.index] : []);
      }
      this.seriesPreview.emit({ seriesId: s.id, points: it.working, changed: [...it.changed] });
    } else {
      const s = this._series.find(q => q.id === it.seriesId)!;
      this.applyBrush({ x: this.fromPx(this.xScale, x), y: this.fromPx(this.yScaleOf(s), y) });
    }
    this.render();
  }

  private applyBrush(p: CurvePoint) {
    const it = this.interaction;
    if (!it || (it.kind !== 'draw' && it.kind !== 'smooth')) return;
    const s = this._series.find(q => q.id === it.seriesId)!;
    const count = this.activeCount(s);
    let changed: number[];
    if (it.kind === 'draw') {
      changed = applyDrawStroke(it.working, it.last.x, it.last.y, p.x, p.y, count, s.y);
    } else {
      const center = nearestIndexByX(it.working, p.x, count);
      changed = applySmoothBrush(it.working, center, Math.max(1, Math.round(this.radius)), 0.5, count, s.y);
    }
    for (const i of changed) it.changed.add(i);
    it.last = p;
    this.seriesPreview.emit({ seriesId: s.id, points: it.working, changed: [...it.changed] });
    this.render();
  }

  onPointerUp(e: PointerEvent) {
    const it = this.interaction;
    this.interaction = null;
    this.frozen = null;
    if (!it) return;
    (e.target as Element).releasePointerCapture?.(e.pointerId);
    if (it.kind === 'marker') {
      if (it.value !== it.original) {
        this.markerChange.emit({ markerId: it.markerId, value: it.value });
      }
    } else if (it.kind !== 'pan') {
      const changed = [...it.changed].sort((a, b) => a - b);
      if (changed.length) {
        this.commit(it.seriesId, it.working, changed);
      }
    }
    this.render();
  }

  onPointerLeave() {
    if (this.interaction) return;
    this.hoverPx = null;
    this.render();
  }

  private commit(seriesId: string, points: CurvePoint[], changed: number[]) {
    // shown until the host passes the new points back
    this.overrides.set(seriesId, points);
    clearTimeout(this.overrideTimer);
    this.overrideTimer = setTimeout(() => {
      this.overrides.clear();
      this.render();
    }, 1500);
    this.seriesChange.emit({ seriesId, points, changed });
  }

  onWheel(e: WheelEvent) {
    if (this.xAxis.categories) return;
    const { x } = this.eventPx(e);
    if (e.ctrlKey || e.metaKey) {
      // ctrl + wheel and trackpad pinch zoom the x axis around the cursor
      e.preventDefault();
      const [d0, d1] = this.zoom ?? [this.xScale.min, this.xScale.max];
      const at = this.fromPx(this.xScale, x);
      const k = Math.exp(e.deltaY * 0.01);
      this.zoom = this.clampZoom(at - (at - d0) * k, at + (d1 - at) * k);
      this.render();
    } else if (this.zoom && (e.shiftKey || Math.abs(e.deltaX) > Math.abs(e.deltaY))) {
      e.preventDefault();
      const delta = (e.shiftKey ? e.deltaY : e.deltaX) || e.deltaY;
      const span = this.zoom[1] - this.zoom[0];
      const shift = (delta / this.plot.width) * span;
      this.zoom = this.clampZoom(this.zoom[0] + shift, this.zoom[1] + shift);
      this.render();
    }
  }

  private clampZoom(a: number, b: number): [number, number] | null {
    this.zoom = null;
    this.computeScales();
    const full: [number, number] = [this.xScale.min, this.xScale.max];
    const fullSpan = full[1] - full[0];
    let span = Math.max(fullSpan / 200, Math.min(fullSpan, b - a));
    if (span >= fullSpan * 0.999) return null;
    a = Math.max(full[0], Math.min(full[1] - span, a));
    return [a, a + span];
  }

  @HostListener('keydown', ['$event'])
  onKeyDown(e: KeyboardEvent) {
    const sel = this.selected;
    if (!sel || this.disabled) {
      if (e.key === 'Escape' && this.zoom) this.resetZoom();
      return;
    }
    const s = this._series.find(q => q.id === sel.seriesId);
    if (!s) return;
    const pts = this.pointsOf(s);
    const canX = s.editable === 'x' || s.editable === 'xy';
    const canY = s.editable === 'y' || s.editable === 'xy';
    const mult = e.shiftKey ? 10 : 1;
    if (e.key === 'Escape') {
      this.selected = null;
    } else if ((e.key === 'ArrowUp' || e.key === 'ArrowDown') && canY) {
      const step = (s.y?.step || this.yScaleOf(s).step / 20) * mult * (e.key === 'ArrowUp' ? 1 : -1);
      this.nudge(s, sel.index, { x: pts[sel.index].x, y: pts[sel.index].y + step });
    } else if ((e.key === 'ArrowLeft' || e.key === 'ArrowRight') && canX && !canY) {
      const step = (s.x?.step || this.xScale.step / 20) * mult * (e.key === 'ArrowRight' ? 1 : -1);
      this.nudge(s, sel.index, { x: pts[sel.index].x + step, y: pts[sel.index].y });
    } else if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
      const dir = e.key === 'ArrowRight' ? 1 : -1;
      let i = sel.index + dir * mult;
      const count = this.activeCount(s);
      i = Math.max(0, Math.min(count - 1, i));
      while (i >= 0 && i < count && s.lockedIndices?.includes(i)) i += dir;
      if (i >= 0 && i < count) this.selected = { seriesId: s.id, index: i };
    } else {
      return;
    }
    e.preventDefault();
    this.render();
  }

  private nudge(s: CurveSeries, index: number, p: CurvePoint) {
    const pts = this.pointsOf(s).map(q => ({ ...q }));
    const o = pts[index];
    let n: CurvePoint = {
      x: p.x !== o.x ? snapValue(p.x, s.x) : o.x,
      y: p.y !== o.y ? snapValue(p.y, s.y) : o.y,
    };
    if (s.constrain) n = s.constrain(index, n);
    if (n.x === o.x && n.y === o.y) return;
    pts[index] = n;
    this.commit(s.id, pts, [index]);
  }

  onSelectedInput(axis: 'x' | 'y', raw: string) {
    const info = this.selectedInfo;
    const v = parseFloat(raw);
    if (!info || !isFinite(v)) return;
    const p = this.pointsOf(info.series)[info.index];
    this.nudge(info.series, info.index, axis === 'x' ? { x: v, y: p.y } : { x: p.x, y: v });
    this.render();
  }

  private roundForInput(v: number, step: number | undefined): number {
    const k = Math.pow(10, step ? decimalsForStep(step) + 1 : 6);
    return Math.round(v * k) / k;
  }

  trackById(_: number, x: { id: string }) {
    return x.id;
  }
}
