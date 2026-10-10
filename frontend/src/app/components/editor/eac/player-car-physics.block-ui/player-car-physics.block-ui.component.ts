import { ChangeDetectionStrategy, Component } from '@angular/core';
import {
  CurveAxis,
  CurveMarker,
  CurveMarkerChange,
  CurvePoint,
  CurveSeries,
  CurveSeriesChange,
} from '../../common/curve-editor/curve-editor.component';
import { StatTile } from '../../common/stat-tiles/stat-tiles.component';
import { SliderSpec } from '../../common/slider-field/slider-field.component';
import {
  angleToDeg,
  ANGLE_FULL,
  CarSpecEditorBase,
  degToAngle,
  floor8Inverse,
  fmt,
  G,
  GEAR_COLORS,
  KW_TO_HP,
  MPS_TO_KMH,
  MPS_TO_MPH,
  ordinal,
  powerKw,
  TICKS,
} from './car-specs';

// the game reads only the first torque rpm and assumes 200 rpm steps
const TORQUE_RPM_STEP = 200;
// grip table index = slip angle (24-bit) >> 12
const GRIP_STEP_DEG = (4096 * 360) / ANGLE_FULL;
const GRIP_LENGTH = 512;
// pedal values at which the brake ramps switch
const BRAKE_RAMP_SWITCH = 144;
// brake force caps switch at these speeds (m/s)
const BRAKE_SPEED_1 = 26.8;
const BRAKE_SPEED_2 = 40;

export type GearRow = {
  index: number;
  name: string;
  color: string;
  ratio: number;
  efficiency: number;
  redlineSpeed: number;
  upshiftIndex: number | null;
  upshift: number | null;
  upshiftSpeed: number | null;
};

export const gearName = (index: number) => (index === 0 ? 'R' : index === 1 ? 'N' : ordinal(index - 1));

// Rich editor of TNFS player car physics (PC SIMDATA/CARSPECS/*.PBS, 3DO DriveData/CarData/*.BigSpecsFam): dyno chart,
// gearing, grip tables, pedals and brakes, with every parameter grouped by subsystem. 3DO files have no gear
// efficiency, a single brake cap in m/s² and per-axle grip multipliers in place of thrust_scale
@Component({
  selector: 'app-player-car-physics-block-ui',
  templateUrl: './player-car-physics.block-ui.component.html',
  styleUrls: ['./player-car-physics.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  standalone: false,
})
export class PlayerCarPhysicsBlockUiComponent extends CarSpecEditorBase {
  readonly groups = {
    engine: [
      'num_torques',
      'min_rpm',
      'max_rpm',
      'thrust_scale',
      'force_to_accel',
      'rpm_acc',
      'rpm_dec',
      'drop_rpm_dec',
      'drop_rpm_inc',
      'neg_torque',
      'unknown_0x320',
      'unknown_0x320_inv',
      'unknown_0x330',
      'burnout_div',
    ],
    gearbox: ['num_gears', 'final_drive', 'mps_to_rpm', 'wheel_radius', 'inv_wheel_rad', 'shift_timer'],
    tires: [
      'friction_f',
      'friction_r',
      'front_grip_mult',
      'front_grip_mult_inv',
      'rear_grip_mult',
      'rear_grip_mult_inv',
      'lat_acc_cutoff',
      'slip_cutoff',
      'max_tire_coeff',
      'normal_loss',
    ],
    brakes: [
      'brake_bias_r',
      'max_brake_force',
      'max_brake_force_1',
      'max_brake_force_2',
      'has_abs',
      'has_tcs',
      'throttle_on_ramp',
      'throttle_off_ramp',
      'brake_on_ramp_1',
      'brake_on_ramp_2',
      'brake_off_ramp_1',
      'brake_off_ramp_2',
    ],
    body: [
      'mass_front',
      'mass_rear',
      'mass',
      'inv_mass_f',
      'inv_mass_r',
      'inv_mass',
      'rear_weight_fraction',
      'cog_height',
      'wheel_base',
      'wheel_base_inv',
      'wheel_track',
      'wheel_track_inv',
      'weight_transfer_factor',
      'inertia_factor',
      'roll_stiff_f',
      'roll_stiff_r',
      'roll_axis_y',
      'front_roll_stiffness_2',
      'rear_roll_stiffness_2',
      'roll_factor',
      'pitch_factor',
      'drag',
      'top_speed',
      'body_len',
      'body_width',
    ],
    steering: [
      'auto_steer',
      'steer_mult',
      'steer_div',
      'steer_model',
      'steer_vel',
      'steer_vel_ramp',
      'steer_vel_att',
      'steer_ramp_mult',
      'steer_ramp_div',
      'incar_camera_height',
      'center_y',
    ],
  };

  // bounded fractions and factors as sliders
  readonly sliders: { [group: string]: [string, SliderSpec][] } = {
    engine: [['efficiency', { min: 0, max: 2, step: 0.01, unit: '×' }]],
    gearbox: [['drive_bias', { min: 0, max: 1, step: 0.01, scale: 100, unit: '% front' }]],
    brakes: [['brake_bias_f', { min: 0, max: 1, step: 0.01, scale: 100, unit: '% front' }]],
  };

  selectedTab = 0;
  tiles: StatTile[] = [];

  // engine
  torqueSeries: CurveSeries[] = [];
  torqueMarkers: CurveMarker[] = [];
  readonly rpmAxis: CurveAxis = { label: 'Engine speed (rpm)', format: v => fmt(v, 0) };
  readonly torqueAxis: CurveAxis = { label: 'Torque (N·m)', min: 0 };
  readonly powerAxis: CurveAxis = { label: 'Power (hp)', min: 0 };
  readonly describeRpm = (rpm: number) =>
    `${fmt(rpm, 0)} rpm · entry ${Math.round((rpm - (this.d['torques'][0]?.rpm || 0)) / TORQUE_RPM_STEP)}`;

  // gearbox
  gears: GearRow[] = [];
  gearSeries: CurveSeries[] = [];
  gearMarkers: CurveMarker[] = [];
  accelSeries: CurveSeries[] = [];
  readonly speedAxis: CurveAxis = { label: 'Speed (km/h)', min: 0, format: v => fmt(v, 0) };
  readonly gearRpmAxis: CurveAxis = { label: 'Engine speed (rpm)', min: 0, format: v => fmt(v, 0) };
  readonly accelAxis: CurveAxis = { label: 'Acceleration (m/s²)', min: 0 };
  readonly describeSpeed = (kmh: number) => `${fmt(kmh, 1)} km/h · ${fmt(kmh / MPS_TO_KMH, 1)} m/s`;

  // tires
  gripSeries: CurveSeries[] = [];
  gripMarkers: CurveMarker[] = [];
  readonly slipAxis: CurveAxis = { label: 'Slip angle (°)', min: 0, format: v => fmt(v, 1) + '°' };
  readonly gripAxis: CurveAxis = { label: 'Grip (value / 128)', min: 0 };
  readonly describeSlip = (deg: number) => `${fmt(deg, 2)}° · entry ${Math.round(deg / GRIP_STEP_DEG)}`;

  // brakes and pedals
  pedalSeries: CurveSeries[] = [];
  brakeSeries: CurveSeries[] = [];
  readonly timeAxis: CurveAxis = { label: 'Time (s)', min: 0 };
  readonly pedalAxis: CurveAxis = { label: 'Pedal (0-255)', min: 0, max: 255, format: v => fmt(v, 0) };
  readonly decelAxis: CurveAxis = { label: 'Max braking (m/s²)', min: 0 };
  readonly describeTime = (s: number) => `${fmt(s, 2)} s · tick ${Math.round(s * TICKS)}`;

  // chassis and steering
  dragSeries: CurveSeries[] = [];
  dragMarkers: CurveMarker[] = [];
  steerSeries: CurveSeries[] = [];
  readonly dragAxis: CurveAxis = { label: 'Drag deceleration (m/s²)', min: 0 };
  readonly steerAxis: CurveAxis = { label: 'Steering rate (per tick)', min: 0 };

  protected refresh(): void {
    const d = this.d;
    if (!d || !Array.isArray(d['torques'])) return;
    this.buildEngine();
    this.buildGears();
    this.buildGrip();
    this.buildBrakes();
    this.buildChassis();
    this.buildTiles();
  }

  // ---------- derived values ----------

  get mass(): number {
    return (this.d['mass_front'] || 0) + (this.d['mass_rear'] || 0);
  }

  // TNFS 3DO (*.BigSpecsFam)
  get is3do(): boolean {
    return !!this.resourceSchema?.block_class_mro?.startsWith('Tnfs3doCarPhysics__');
  }

  get forceToAccel(): number {
    return floor8Inverse(this.d['thrust_scale']);
  }

  private get numTorques(): number {
    return Math.max(0, Math.min(this.d['torques'].length, this.d['num_torques'] || 0));
  }

  private get numGears(): number {
    return Math.max(0, Math.min(this.d['gear_ratios'].length, this.d['num_gears'] || 0));
  }

  private get numUpshifts(): number {
    return Math.max(0, Math.min(this.d['upshifts'].length, this.numGears - 3));
  }

  torqueRpm(i: number): number {
    return (this.d['torques'][0]?.rpm || 0) + TORQUE_RPM_STEP * i;
  }

  // engine torque the game reads at `rpm` (nearest 200 rpm entry)
  torqueAt(rpm: number, torques: { rpm: number; torque: number }[] = this.d['torques']): number {
    const i = Math.round((rpm - (torques[0]?.rpm || 0)) / TORQUE_RPM_STEP);
    return torques[Math.max(0, Math.min(this.numTorques - 1, i))]?.torque || 0;
  }

  // m/s at `rpm` in the gear with ratio `ratio`
  speedAt(rpm: number, ratio: number): number {
    const k = (this.d['mps_to_rpm'] || 0) * Math.abs(ratio);
    return k > 0 ? rpm / k : 0;
  }

  private peak(torques: { rpm: number; torque: number }[]) {
    let power = { kw: 0, rpm: 0 };
    let torque = { nm: 0, rpm: 0 };
    const min = this.d['min_rpm'] || 0;
    const max = this.d['max_rpm'] || Infinity;
    for (let i = 0; i < this.numTorques; i++) {
      const rpm = this.torqueRpm(i);
      if (rpm < min - TORQUE_RPM_STEP / 2 || rpm > max + TORQUE_RPM_STEP / 2) continue;
      const t = torques[i].torque;
      const kw = powerKw(t, rpm);
      if (kw > power.kw) power = { kw, rpm };
      if (t > torque.nm) torque = { nm: t, rpm };
    }
    return { power, torque };
  }

  // ---------- engine ----------

  private buildEngine(torques: { rpm: number; torque: number }[] = this.d['torques']) {
    const d = this.d;
    const points = torques.map((t, i) => ({ x: this.torqueRpm(i), y: t.torque }));
    this.torqueSeries = [
      {
        id: 'torque',
        label: 'Torque',
        color: '#3f51b5',
        points,
        editable: 'y',
        activeCount: this.numTorques,
        y: { min: 0, step: 1 },
        formatY: v => fmt(v, 0) + ' N·m',
      },
      {
        id: 'power',
        label: 'Power',
        color: '#e64a19',
        axis: 'right',
        points: points.map(p => ({ x: p.x, y: powerKw(p.y, p.x) * KW_TO_HP })),
        activeCount: this.numTorques,
        formatY: v => `${fmt(v, 0)} hp · ${fmt(v / KW_TO_HP, 0)} kW`,
      },
    ];
    this.torqueMarkers = [
      {
        id: 'min_rpm',
        value: d['min_rpm'],
        label: 'Idle',
        color: '#607d8b',
        editable: true,
        constraints: { min: 0, step: 50 },
        format: v => fmt(v, 0),
      },
      {
        id: 'max_rpm',
        value: d['max_rpm'],
        label: 'Redline',
        color: '#d32f2f',
        editable: true,
        constraints: { min: 500, step: 50 },
        format: v => fmt(v, 0),
      },
    ];
  }

  onTorquePreview(e: CurveSeriesChange) {
    // live power curve and peaks while dragging
    const torques = this.d['torques'].map((t: any, i: number) => ({ rpm: t.rpm, torque: e.points[i].y }));
    const power = this.torqueSeries[1];
    this.torqueSeries = [
      this.torqueSeries[0],
      { ...power, points: e.points.map(p => ({ x: p.x, y: powerKw(p.y, p.x) * KW_TO_HP })) },
    ];
    this.buildTiles(torques);
  }

  onTorqueChange(e: CurveSeriesChange) {
    const torques = this.d['torques'].map((t: any) => ({ ...t }));
    for (const i of e.changed) {
      // the game reads only the first rpm and assumes 200 rpm steps: keep the edited entries consistent with that
      torques[i] = { rpm: i === 0 ? torques[0].rpm : this.torqueRpm(i), torque: Math.round(e.points[i].y) };
    }
    this.setValue(['torques'], torques);
  }

  onRpmMarker(e: CurveMarkerChange) {
    this.setValue([e.markerId], Math.round(e.value));
  }

  // ---------- gearbox ----------

  private buildGears(ratios: number[] = this.d['gear_ratios'], upshifts: number[] = this.d['upshifts']) {
    const d = this.d;
    const maxRpm = d['max_rpm'] || 0;
    this.gears = [];
    for (let i = 0; i < this.numGears; i++) {
      const upshiftIndex = i >= 2 && i - 2 < this.numUpshifts ? i - 2 : null;
      const upshift = upshiftIndex !== null ? upshifts[upshiftIndex] : null;
      this.gears.push({
        index: i,
        name: gearName(i),
        color: i >= 2 ? GEAR_COLORS[(i - 2) % GEAR_COLORS.length] : '#9e9e9e',
        ratio: ratios[i],
        efficiency: d['gear_efficiency']?.[i] ?? 1,
        redlineSpeed: this.speedAt(maxRpm, ratios[i]) * MPS_TO_KMH,
        upshiftIndex,
        upshift,
        upshiftSpeed: upshift !== null ? this.speedAt(upshift, ratios[i]) * MPS_TO_KMH : null,
      });
    }
    const forward = this.gears.filter(g => g.index >= 2);

    this.gearSeries = forward.map(g => ({
      id: 'gear-' + g.index,
      label: g.name,
      color: g.color,
      points: [
        { x: 0, y: 0 },
        { x: g.redlineSpeed, y: maxRpm },
      ],
      editable: 'x' as const,
      lockedIndices: [0],
      x: { min: 1, step: 0.1 },
      pointLabels: ['', 'speed at the redline, drag to change the ratio'],
      formatY: v => fmt(v, 0) + ' rpm',
    }));
    const shifts = forward.filter(g => g.upshift !== null);
    const drops: CurvePoint[] = [];
    for (const g of shifts) {
      const next = this.gears[g.index + 1];
      if (!next) continue;
      const v = g.upshiftSpeed! / MPS_TO_KMH;
      drops.push(
        { x: g.upshiftSpeed!, y: g.upshift! },
        { x: g.upshiftSpeed!, y: v * (d['mps_to_rpm'] || 0) * Math.abs(next.ratio) },
        { x: NaN, y: NaN },
      );
    }
    this.gearSeries.push(
      {
        id: 'shift-drops',
        label: 'Rpm drop',
        color: '#9e9e9e',
        points: drops,
        dashed: true,
        strokeWidth: 1,
        hideInLegend: true,
        inTooltip: false,
      },
      {
        id: 'upshifts',
        label: 'Automatic upshift',
        color: '#424242',
        style: 'points',
        points: shifts.map(g => ({ x: g.upshiftSpeed!, y: g.upshift! })),
        pointLabels: shifts.map(g => `${g.name} → ${gearName(g.index + 1)}`),
        editable: 'y',
        y: { min: 0, step: 50 },
        constrain: (i, p) => ({ x: this.speedAt(p.y, shifts[i].ratio) * MPS_TO_KMH, y: p.y }),
        formatY: v => fmt(v, 0) + ' rpm',
      },
    );
    this.gearMarkers = [
      {
        id: 'max_rpm',
        value: maxRpm,
        orientation: 'horizontal',
        label: 'Redline',
        color: '#d32f2f',
        editable: true,
        constraints: { min: 500, step: 50 },
        format: v => fmt(v, 0),
      },
      {
        id: 'top_speed',
        value: (d['top_speed'] || 0) * MPS_TO_KMH,
        label: 'Top speed',
        color: '#455a64',
        editable: true,
        constraints: { min: 1, step: 0.5 },
        format: v => fmt(v, 0) + ' km/h',
      },
    ];

    // drive acceleration by speed in each gear, from the torque table formula of the game (no drag, no grip limit)
    const k = ((d['final_drive'] || 0) * (d['efficiency'] || 0)) / ((d['wheel_radius'] || 1) * (this.mass || 1));
    this.accelSeries = forward.map(g => {
      const points: CurvePoint[] = [];
      for (let i = 0; i < this.numTorques; i++) {
        const rpm = this.torqueRpm(i);
        if (rpm < (d['min_rpm'] || 0) || rpm > maxRpm) continue;
        points.push({
          x: this.speedAt(rpm, g.ratio) * MPS_TO_KMH,
          y: this.d['torques'][i].torque * k * Math.abs(g.ratio) * (g.efficiency || 0),
        });
      }
      return {
        id: 'accel-' + g.index,
        label: g.name,
        color: g.color,
        points,
        formatY: (v: number) => `${fmt(v, 2)} m/s² · ${fmt(v / G, 2)} g`,
      };
    });
  }

  onGearPreview(e: CurveSeriesChange) {
    const ratios = [...this.d['gear_ratios']];
    const upshifts = [...this.d['upshifts']];
    if (e.seriesId.startsWith('gear-')) {
      ratios[+e.seriesId.substring(5)] = this.ratioForSpeed(e.points[1].x);
    } else if (e.seriesId === 'upshifts') {
      const shifts = this.gears.filter(g => g.upshiftIndex !== null);
      e.points.forEach((p, i) => (upshifts[shifts[i].upshiftIndex!] = Math.round(p.y)));
    } else {
      return;
    }
    this.buildGears(ratios, upshifts);
  }

  onGearChange(e: CurveSeriesChange) {
    if (e.seriesId.startsWith('gear-')) {
      this.setValue(['gear_ratios', +e.seriesId.substring(5)], this.ratioForSpeed(e.points[1].x));
    } else if (e.seriesId === 'upshifts') {
      const shifts = this.gears.filter(g => g.upshiftIndex !== null);
      this.setValues(e.changed.map(i => [['upshifts', shifts[i].upshiftIndex!], Math.round(e.points[i].y)]));
    }
  }

  onGearMarker(e: CurveMarkerChange) {
    if (e.markerId === 'top_speed') {
      this.setValue(['top_speed'], Math.round((e.value / MPS_TO_KMH) * 100) / 100);
    } else {
      this.setValue([e.markerId], Math.round(e.value));
    }
  }

  // gear ratio that reaches `kmh` at the redline
  private ratioForSpeed(kmh: number): number {
    const k = (this.d['mps_to_rpm'] || 0) * (kmh / MPS_TO_KMH);
    return k > 0 ? Math.round(((this.d['max_rpm'] || 0) / k) * 1000) / 1000 : 0;
  }

  // ---------- tires ----------

  private get gripActiveCount(): number {
    return Math.max(1, Math.min(GRIP_LENGTH, Math.floor((this.d['slip_cutoff'] || 0) / 4096) + 1));
  }

  private buildGrip() {
    const table = (raw: number[]) => raw.map((v, i) => ({ x: i * GRIP_STEP_DEG, y: v / 128 }));
    const common = {
      editable: 'y' as const,
      activeCount: this.gripActiveCount,
      y: { min: 0, max: 255 / 128, step: 1 / 128 },
      formatY: (v: number) => `${fmt(v, 3)} (${Math.round(v * 128)})`,
    };
    this.gripSeries = [
      { id: 'grip_table_f', label: 'Front', color: '#1e88e5', points: table(this.d['grip_table_f']), ...common },
      { id: 'grip_table_r', label: 'Rear', color: '#f4511e', points: table(this.d['grip_table_r']), ...common },
    ];
    this.gripMarkers = [
      {
        id: 'slip_cutoff',
        value: angleToDeg(this.d['slip_cutoff'] || 0),
        label: 'Slip cutoff',
        color: '#6d4c41',
        editable: true,
        constraints: { min: GRIP_STEP_DEG, max: (GRIP_LENGTH - 1) * GRIP_STEP_DEG, step: GRIP_STEP_DEG / 16 },
        format: v => fmt(v, 2) + '°',
      },
    ];
  }

  onGripChange(e: CurveSeriesChange) {
    const raw = [...this.d[e.seriesId]];
    for (const i of e.changed) raw[i] = Math.max(0, Math.min(255, Math.round(e.points[i].y * 128)));
    this.setValue([e.seriesId], raw);
  }

  onGripMarker(e: CurveMarkerChange) {
    this.setValue(['slip_cutoff'], degToAngle(e.value));
  }

  copyGrip(from: 'grip_table_f' | 'grip_table_r') {
    const to = from === 'grip_table_f' ? 'grip_table_r' : 'grip_table_f';
    this.setValue([to], [...this.d[from]]);
  }

  get gripTablesEqual(): boolean {
    const f = this.d['grip_table_f'] as number[];
    const r = this.d['grip_table_r'] as number[];
    return f.every((v, i) => v === r[i]);
  }

  // ---------- brakes and pedals ----------

  private buildBrakes() {
    const d = this.d;
    const ramp = (start: number, step: (v: number) => number, rising: boolean): CurvePoint[] => {
      const pts: CurvePoint[] = [{ x: 0, y: start }];
      let v = start;
      for (let t = 1; t <= 10 * TICKS; t++) {
        const s = step(v);
        if (!(s > 0)) break;
        v = rising ? Math.min(255, v + s) : Math.max(0, v - s);
        pts.push({ x: t / TICKS, y: v });
        if (v === (rising ? 255 : 0)) break;
      }
      return pts;
    };
    this.pedalSeries = [
      {
        id: 'throttle_on',
        label: 'Throttle press',
        color: '#43a047',
        points: ramp(0, () => d['throttle_on_ramp'], true),
      },
      {
        id: 'throttle_off',
        label: 'Throttle release',
        color: '#43a047',
        dashed: true,
        points: ramp(255, () => d['throttle_off_ramp'], false),
      },
      {
        id: 'brake_on',
        label: 'Brake press',
        color: '#e53935',
        points: ramp(0, v => (v < BRAKE_RAMP_SWITCH ? d['brake_on_ramp_1'] : d['brake_on_ramp_2']) * 1.25, true),
      },
      {
        id: 'brake_off',
        label: 'Brake release',
        color: '#e53935',
        dashed: true,
        points: ramp(255, v => (v < BRAKE_RAMP_SWITCH ? d['brake_off_ramp_1'] : d['brake_off_ramp_2']), false),
      },
    ].map(s => ({ ...s, style: 'step' as const, formatY: (v: number) => fmt(v, 0) }));

    const end = Math.max(BRAKE_SPEED_2 * 1.4, (d['top_speed'] || 0) * 1.05) * MPS_TO_KMH;
    const formatY = (v: number) => `${fmt(v, 1)} m/s² · ${fmt(v / G, 2)} g`;
    if (this.is3do) {
      // `tnfs_physics_update` (3DO): one cap at every speed, already an acceleration
      const a = d['max_brake_force'] || 0;
      this.brakeSeries = [
        {
          id: 'brake_decel',
          label: 'Brake force cap',
          color: '#c62828',
          style: 'step',
          points: [
            { x: 0, y: a },
            { x: end, y: a },
          ],
          editable: 'y',
          lockedIndices: [1],
          y: { min: 0, step: 0.1 },
          pointLabels: ['max_brake_force', ''],
          formatY,
        },
      ];
      return;
    }
    const fta = this.forceToAccel;
    const a1 = (d['max_brake_force_1'] || 0) * fta;
    const a2 = (d['max_brake_force_2'] || 0) * fta;
    this.brakeSeries = [
      {
        id: 'brake_decel',
        label: 'Brake force cap',
        color: '#c62828',
        style: 'step',
        points: [
          { x: 0, y: a1 },
          { x: BRAKE_SPEED_1 * MPS_TO_KMH, y: a2 },
          { x: BRAKE_SPEED_2 * MPS_TO_KMH, y: Math.max(a1, a2) },
          { x: end, y: Math.max(a1, a2) },
        ],
        editable: fta > 0 ? 'y' : 'none',
        lockedIndices: [2, 3],
        y: { min: 0, step: 0.1 },
        pointLabels: [
          'below 60 mph: max_brake_force_1',
          '60-90 mph: max_brake_force_2',
          'above 90 mph: larger one',
          '',
        ],
        formatY,
      },
    ];
  }

  onBrakeChange(e: CurveSeriesChange) {
    if (this.is3do) {
      if (e.changed.includes(0)) this.setValue(['max_brake_force'], Math.round(e.points[0].y * 100) / 100);
      return;
    }
    const fta = this.forceToAccel;
    if (!fta) return;
    const entries: [(string | number)[], any][] = [];
    if (e.changed.includes(0)) entries.push([['max_brake_force_1'], Math.round((e.points[0].y / fta) * 100) / 100]);
    if (e.changed.includes(1)) entries.push([['max_brake_force_2'], Math.round((e.points[1].y / fta) * 100) / 100]);
    this.setValues(entries);
  }

  // ---------- chassis and steering ----------

  private buildChassis() {
    const d = this.d;
    const top = d['top_speed'] || 0;
    const end = Math.max(top * 1.2, 30);
    const dragK = (d['drag'] || 0) / (this.mass || 1);
    const pts: CurvePoint[] = [];
    for (let v = 0; v <= end + 1e-9; v += end / 60) pts.push({ x: v * MPS_TO_KMH, y: dragK * v * v });
    this.dragSeries = [
      {
        id: 'drag',
        label: 'Air drag',
        color: '#00897b',
        points: pts,
        formatY: v => `${fmt(v, 2)} m/s² · ${fmt(v / G, 2)} g`,
      },
    ];
    this.dragMarkers = [
      {
        id: 'top_speed',
        value: top * MPS_TO_KMH,
        label: 'Top speed',
        color: '#455a64',
        editable: true,
        constraints: { min: 1, step: 0.5 },
        format: v => fmt(v, 0) + ' km/h',
      },
    ];

    // `tnfs_control_steering_a` (3DO `tnfs_control_steering`): rate per tick = min(steer_vel_ramp - min(speed * steer_vel_att, 1.5), 1.6) * steer_vel[1]
    const rate = (v: number) =>
      Math.min((d['steer_vel_ramp'] || 0) - Math.min(v * (d['steer_vel_att'] || 0), 1.5), 1.6) *
      (d['steer_vel']?.[1] || 0);
    const steer: CurvePoint[] = [];
    for (let v = 0; v <= end + 1e-9; v += end / 60) steer.push({ x: v * MPS_TO_KMH, y: Math.max(0, rate(v)) });
    this.steerSeries = [
      { id: 'steer', label: 'Steering rate', color: '#5e35b1', points: steer, formatY: v => fmt(v, 2) + ' / tick' },
    ];
  }

  // ---------- summary ----------

  private buildTiles(torques: { rpm: number; torque: number }[] = this.d['torques']) {
    const d = this.d;
    const { power, torque } = this.peak(torques);
    const hp = power.kw * KW_TO_HP;
    const mass = this.mass;
    const bias = d['drive_bias'] || 0;
    const drive = bias <= 0 ? 'RWD' : bias >= 1 ? 'FWD' : 'AWD';
    const top = d['top_speed'] || 0;
    const aids = [d['has_abs'] > 0 ? 'ABS' : '', d['has_tcs'] > 0 ? 'TCS' : ''].filter(x => x).join(' + ');
    const forwardGears = Math.max(0, this.numGears - 2);
    this.tiles = [
      {
        id: 'peak_power',
        label: 'Peak power',
        value: `${fmt(hp, 0)} hp`,
        edit: { value: Math.round(hp), step: 1, min: 1, unit: 'hp' },
        sub: `${fmt(power.kw, 0)} kW @ ${fmt(power.rpm, 0)} rpm`,
        hint: 'Peak of the torque curve between idle and redline. A new value scales the whole torque curve',
        tone: 'accent',
      },
      {
        id: 'peak_torque',
        label: 'Peak torque',
        value: `${fmt(torque.nm, 0)} N·m`,
        edit: { value: Math.round(torque.nm), step: 1, min: 1, unit: 'N·m' },
        sub: `@ ${fmt(torque.rpm, 0)} rpm`,
        hint: 'A new value scales the whole torque curve',
        tone: 'accent',
      },
      {
        id: 'max_rpm',
        label: 'Redline',
        value: `${fmt(d['max_rpm'], 0)} rpm`,
        edit: { value: d['max_rpm'], step: 50, min: 500, unit: 'rpm' },
        sub: `idle ${fmt(d['min_rpm'], 0)} rpm`,
        hint: 'max_rpm',
      },
      {
        id: 'mass',
        label: 'Mass',
        value: `${fmt(mass, 0)} kg`,
        edit: { value: Math.round(mass), step: 5, min: 1, unit: 'kg' },
        sub: `${fmt(mass ? (d['mass_front'] / mass) * 100 : 0, 0)}% front · ${fmt(mass ? (hp / mass) * 1000 : 0, 0)} hp/t`,
        hint: 'mass_front + mass_rear. A new value keeps the front / rear split',
      },
      {
        id: 'top_speed',
        label: 'Top speed',
        value: `${fmt(top * MPS_TO_KMH, 0)} km/h`,
        edit: { value: Math.round(top * MPS_TO_KMH), step: 1, min: 1, unit: 'km/h' },
        sub: `${fmt(top * MPS_TO_MPH, 0)} mph · ${fmt(top, 1)} m/s`,
        hint: 'top_speed',
      },
      {
        label: 'Drivetrain',
        value: drive,
        sub: `${forwardGears}-speed · final ${fmt(d['final_drive'], 2)}`,
        hint:
          (drive === 'AWD' ? `${fmt(bias * 100, 0)}% of the drive force on the front axle. ` : '') +
          'Set by the drive_bias slider in the Gearbox tab',
      },
      {
        id: 'brake_bias_f',
        label: 'Brakes',
        value: `${fmt((d['brake_bias_f'] || 0) * 100, 0)}% front`,
        edit: { value: Math.round((d['brake_bias_f'] || 0) * 100), step: 1, min: 0, max: 100, unit: '% front' },
        sub: aids || 'no ABS / TCS',
        hint: 'brake_bias_f',
      },
    ];
    if (!d['efficiency']) {
      this.tiles.push({
        label: 'Efficiency',
        value: '0',
        sub: 'the car has no drive force',
        tone: 'warn',
        hint: this.is3do ? '' : 'The game also zeroes it on a checksum mismatch; the checksum is recomputed on save',
      });
    }
  }

  onTileChange(e: { id: string; value: number }) {
    const d = this.d;
    if (e.id === 'peak_power' || e.id === 'peak_torque') {
      const { power, torque } = this.peak(d['torques']);
      const old = e.id === 'peak_power' ? power.kw * KW_TO_HP : torque.nm;
      if (!old) return;
      const k = e.value / old;
      const torques = d['torques'].map((t: any, i: number) =>
        i < this.numTorques ? { ...t, torque: Math.max(0, Math.round(t.torque * k)) } : t,
      );
      this.setValue(['torques'], torques);
    } else if (e.id === 'mass') {
      const k = e.value / (this.mass || 1);
      this.setValues([
        [['mass_front'], this.round(d['mass_front'] * k, 2)],
        [['mass_rear'], this.round(d['mass_rear'] * k, 2)],
      ]);
    } else if (e.id === 'top_speed') {
      this.setValue(['top_speed'], this.round(e.value / MPS_TO_KMH, 2));
    } else if (e.id === 'brake_bias_f') {
      this.setValue(['brake_bias_f'], Math.max(0, Math.min(1, e.value / 100)));
    } else if (e.id === 'max_rpm') {
      this.setValue(['max_rpm'], Math.round(e.value));
    }
  }

  readonly fmt = fmt;

  round(v: number, digits: number): number {
    const k = Math.pow(10, digits);
    return Math.round(v * k) / k;
  }
}
