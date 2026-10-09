import { ChangeDetectionStrategy, Component } from '@angular/core';
import {
  CurveAxis,
  CurveMarker,
  CurveMarkerChange,
  CurveSeries,
  CurveSeriesChange,
} from '../../common/curve-editor/curve-editor.component';
import { StatTile } from '../../common/stat-tiles/stat-tiles.component';
import { SliderSpec } from '../../common/slider-field/slider-field.component';
import {
  angleToDeg,
  CarSpecEditorBase,
  degToAngle,
  fmt,
  GEAR_COLORS,
  MPS_TO_KMH,
  ordinal,
} from '../player-car-physics.block-ui/car-specs';

// `handling_factor` of traffic, cops, TSUPRA and TRAFFC: no corner slowdown
const NO_CORNER_SLOWDOWN = 0xff0000;
// horn pitch table of the game (DOS 0x81aa9), indexed by `gear_count`
const HORN_PITCH = [0x40, 0x40, 0x64, 0x5a, 0x50, 0x46, 0x3c, 0x32, 0x2d, 0x28];
const TURN_AXIS_MAX_DEG = 30;

// Rich editor of a TNFS car AI and crash body (SIMDATA/CARFAMS/*.PDN): AI acceleration curve with the gear top
// speeds, corner slowdown and the collision box
@Component({
  selector: 'app-car-ai-and-crash-body-block-ui',
  templateUrl: './car-ai-and-crash-body.block-ui.component.html',
  styleUrls: ['./car-ai-and-crash-body.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  standalone: false,
})
export class CarAiAndCrashBodyBlockUiComponent extends CarSpecEditorBase {
  readonly groups = {
    body: ['half_width', 'half_height', 'half_length'],
    ai: ['handling_factor', 'max_rpm', 'gear_count', 'top_speeds'],
  };
  // bounded factors as sliders, over the range of the shipped files with some room
  readonly sliders: { body: [string, SliderSpec][]; ai: [string, SliderSpec][] } = {
    body: [
      ['mass', { min: 0.25, max: 2, step: 0.01, unit: '×' }],
      ['moment_of_inertia', { min: 0.5, max: 3, step: 0.01 }],
    ],
    ai: [['speed_factor', { min: 0.8, max: 1.2, step: 0.005, unit: '×' }]],
  };

  tiles: StatTile[] = [];
  powerSeries: CurveSeries[] = [];
  powerMarkers: CurveMarker[] = [];
  cornerSeries: CurveSeries[] = [];
  cornerMarkers: CurveMarker[] = [];
  box = { length: 0, width: 0, height: 0, k: 1, fromModel: false };

  readonly speedAxis: CurveAxis = { label: 'Speed (m/s), entry = speed + 1', min: -1 };
  readonly gainAxis: CurveAxis = { label: 'Speed gain per AI update', min: 0 };
  readonly turnAxis: CurveAxis = { label: 'Road heading change per node (°)', min: 0, max: TURN_AXIS_MAX_DEG };
  readonly factorAxis: CurveAxis = { label: 'Target speed ×' };
  readonly describeSpeed = (v: number) =>
    `${fmt(v, 1)} m/s · ${fmt(v * MPS_TO_KMH, 0)} km/h · entry ${Math.round(v) + 1}`;
  readonly describeTurn = (deg: number) => `${fmt(deg, 2)}° per node`;
  readonly fmt = fmt;

  protected refresh(): void {
    const d = this.d;
    if (!d || !Array.isArray(d['power_curve'])) return;
    this.buildPower();
    this.buildCorner();
    const length = (d['half_length'] || 0) * 2;
    const width = (d['half_width'] || 0) * 2;
    const height = (d['half_height'] || 0) * 2;
    this.box = {
      length,
      width,
      height,
      // svg units per m: the box fits 220 x 70 in both views
      k: Math.min(220 / (length || 1), 70 / (Math.max(width, height) || 1)),
      fromModel: !length || !width || !height,
    };
    this.buildTiles();
  }

  get isRacer(): boolean {
    return this.d['top_speeds'].some((v: number) => v > 0);
  }

  get handlingDeg(): number | null {
    const h = this.d['handling_factor'];
    return h === NO_CORNER_SLOWDOWN || !h ? null : angleToDeg(h);
  }

  get hornPitch(): number | undefined {
    return HORN_PITCH[this.d['gear_count']];
  }

  private buildPower() {
    const curve = this.d['power_curve'] as number[];
    this.powerSeries = [
      {
        id: 'power_curve',
        label: 'AI acceleration',
        color: '#3f51b5',
        // entry = |speed| + 1
        points: curve.map((y, i) => ({ x: i - 1, y })),
        editable: 'y',
        y: { min: 0 },
        formatY: v => fmt(v, 4),
      },
    ];
    this.powerMarkers = (this.d['top_speeds'] as number[])
      .map((v, i) => ({ v, i }))
      .filter(({ v }) => v > 0)
      .map(({ v, i }, n, all) => ({
        id: 'top_speeds/' + i,
        value: v,
        // gears with a top speed of 0 are skipped: name the used ones from 1st
        label: ordinal(n + 1),
        color: GEAR_COLORS[n % GEAR_COLORS.length],
        editable: true,
        constraints: { min: 0.5, step: 0.1 },
        format: (x: number) => `${fmt(x * MPS_TO_KMH, 0)} km/h`,
      }));
  }

  private buildCorner() {
    const h = angleToDeg(this.d['handling_factor'] || 0);
    const factor = (turn: number) => (h ? 0.8 + 0.203 * (1 - turn / h) : 0.8);
    this.cornerSeries = [
      {
        id: 'corner',
        label: 'Target speed factor',
        color: '#00897b',
        points: [
          { x: 0, y: factor(0) },
          { x: TURN_AXIS_MAX_DEG, y: factor(TURN_AXIS_MAX_DEG) },
        ],
        formatY: v => '× ' + fmt(v, 3),
      },
    ];
    this.cornerMarkers =
      h > 0 && h <= TURN_AXIS_MAX_DEG
        ? [
            {
              id: 'handling_factor',
              value: h,
              label: 'Handling factor',
              color: '#6d4c41',
              editable: true,
              constraints: { min: 0.5, max: TURN_AXIS_MAX_DEG, step: 0.05 },
              format: v => fmt(v, 2) + '°',
            },
          ]
        : [];
  }

  onPowerChange(e: CurveSeriesChange) {
    const curve = [...this.d['power_curve']];
    for (const i of e.changed) curve[i] = e.points[i].y;
    this.setValue(['power_curve'], curve);
  }

  onPowerMarker(e: CurveMarkerChange) {
    this.setValue(['top_speeds', +e.markerId.split('/')[1]], Math.round(e.value * 100) / 100);
  }

  onCornerMarker(e: CurveMarkerChange) {
    this.setValue(['handling_factor'], degToAngle(e.value));
  }

  toggleCornerSlowdown(enabled: boolean) {
    this.setValue(['handling_factor'], enabled ? 0xa0000 : NO_CORNER_SLOWDOWN);
  }

  private buildTiles() {
    const d = this.d;
    const top = Math.max(0, ...(d['top_speeds'] as number[]));
    const h = this.handlingDeg;
    this.tiles = [
      {
        label: 'Collision box',
        value: this.box.fromModel ? 'From 3D model' : `${fmt(this.box.length, 2)} × ${fmt(this.box.width, 2)} m`,
        sub: this.box.fromModel ? 'a half size is 0' : `height ${fmt(this.box.height, 2)} m`,
        hint: 'Three values: edit the half sizes under Collision body',
        tone: this.box.fromModel ? 'muted' : 'default',
      },
      {
        id: 'mass',
        label: 'Crash mass',
        value: '× ' + fmt(d['mass'], 2),
        edit: { value: this.round(d['mass'], 3), step: 0.05, min: 0, unit: '×' },
        sub: `inertia ${fmt(d['moment_of_inertia'], 2)}`,
        hint: 'Relative crash-body mass (mass), no physical unit',
      },
      top > 0
        ? {
            id: 'top_speed',
            label: 'AI top speed',
            value: `${fmt(top * MPS_TO_KMH, 0)} km/h`,
            edit: { value: Math.round(top * MPS_TO_KMH), step: 1, min: 1, unit: 'km/h' },
            sub: `${fmt(top, 1)} m/s`,
            hint: 'Top speed of the top gear. A new value scales the top speed of every gear',
            tone: 'accent' as const,
          }
        : {
            label: 'AI top speed',
            value: '–',
            sub: 'no gears: traffic or cop',
            hint: 'All top_speeds are 0: the AI does not use gears',
            tone: 'muted' as const,
          },
      {
        id: 'speed_factor',
        label: 'Speed factor',
        value: '× ' + fmt(d['speed_factor'], 3),
        edit: { value: this.round(d['speed_factor'], 4), step: 0.005, min: 0, unit: '×' },
        sub: 'racers only',
        hint: 'Target speed multiplier of a racer (speed_factor)',
      },
      h
        ? {
            id: 'handling_factor',
            label: 'Corner slowdown',
            value: fmt(h, 1) + '°',
            edit: { value: this.round(h, 2), step: 0.1, min: 0.1, unit: '°' },
            sub: 'handling factor',
            hint: 'Road heading change per node at which a racer slows down to 0.8 of its target speed',
          }
        : {
            label: 'Corner slowdown',
            value: 'None',
            sub: '0xFF0000',
            hint: 'Turn it on with "Slow down in corners" below',
            tone: 'muted' as const,
          },
      {
        id: 'gear_count',
        label: 'Horn pitch index',
        value: '' + d['gear_count'],
        edit: { value: d['gear_count'], step: 1, min: 0, max: HORN_PITCH.length - 1 },
        sub: this.hornPitch !== undefined ? `pitch 0x${this.hornPitch.toString(16)}` : 'out of the pitch table',
        hint: 'gear_count: index into the traffic horn pitch table of the game',
      },
    ];
  }

  onTileChange(e: { id: string; value: number }) {
    if (e.id === 'top_speed') {
      const speeds = this.d['top_speeds'] as number[];
      const k = e.value / MPS_TO_KMH / Math.max(...speeds);
      this.setValues(speeds.map((v, i) => [['top_speeds', i], Math.round(v * k * 100) / 100]));
    } else if (e.id === 'handling_factor') {
      this.setValue(['handling_factor'], degToAngle(e.value));
    } else if (e.id === 'gear_count') {
      this.setValue(['gear_count'], Math.max(0, Math.round(e.value)));
    } else {
      this.setValue([e.id], e.value);
    }
  }

  round(v: number, digits: number): number {
    const k = Math.pow(10, digits);
    return Math.round(v * k) / k;
  }
}
