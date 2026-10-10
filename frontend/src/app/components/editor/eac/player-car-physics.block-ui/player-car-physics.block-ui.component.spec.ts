import { NO_ERRORS_SCHEMA } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { BehaviorSubject, Subject } from 'rxjs';
import { PlayerCarPhysicsBlockUiComponent } from './player-car-physics.block-ui.component';
import { MainService } from '../../../../services/main.service';
import { ChangesService } from '../../../../services/changes.service';

// ANSX.PBS figures
const spec = () => ({
  mass_front: 702.5,
  mass_rear: 702.5,
  drive_bias: 0,
  brake_bias_f: 0.66,
  max_brake_force_1: 25.5,
  max_brake_force_2: 37.5,
  top_speed: 75,
  efficiency: 0.68,
  wheel_radius: 0.32,
  mps_to_rpm: 128.46,
  num_gears: 7,
  final_drive: 4.06,
  gear_ratios: [-1.909, 3.07, 3.07, 1.73, 1.23, 0.97, 0.77, 1338.39],
  gear_efficiency: [1, 1, 1, 1.035, 1.113, 1.094, 1.113, -1131074],
  upshifts: [7900, 7900, 7900, 7900, 553909377, 4138985095, 2164522344],
  num_torques: 51,
  torques: Array.from({ length: 60 }, (_, i) => ({ rpm: 1000 + 200 * i, torque: i < 51 ? 200 + i : 0 })),
  min_rpm: 700,
  max_rpm: 8000,
  slip_cutoff: 0x1fe667,
  thrust_scale: 2.5,
  has_abs: 1,
  has_tcs: 1,
  grip_table_f: Array.from({ length: 512 }, () => 100),
  grip_table_r: Array.from({ length: 512 }, () => 120),
  steer_vel: [2, 4, 8, 16],
  steer_vel_ramp: 2.2,
  steer_vel_att: 0.05,
  drag: 0.275,
  throttle_on_ramp: 25,
  throttle_off_ramp: 17,
  brake_on_ramp_1: 17,
  brake_on_ramp_2: 2,
  brake_off_ramp_1: 25,
  brake_off_ramp_2: 7,
});

describe('PlayerCarPhysicsBlockUiComponent', () => {
  let fixture: ComponentFixture<PlayerCarPhysicsBlockUiComponent>;
  let component: PlayerCarPhysicsBlockUiComponent;
  let appendChanges: jasmine.Spy;

  beforeEach(async () => {
    appendChanges = jasmine.createSpy('appendChanges').and.returnValue(Promise.resolve());
    await TestBed.configureTestingModule({
      declarations: [PlayerCarPhysicsBlockUiComponent],
      providers: [
        { provide: MainService, useValue: { focusedResourceId$: new BehaviorSubject(null) } },
        {
          provide: ChangesService,
          useValue: {
            change$: new Subject<string>(),
            appendChanges,
            subscribeComponent: () => {},
            unsubscribeComponent: () => {},
          },
        },
      ],
      schemas: [NO_ERRORS_SCHEMA],
    }).compileComponents();
    fixture = TestBed.createComponent(PlayerCarPhysicsBlockUiComponent);
    component = fixture.componentInstance;
    component.resourceId = 'ANSX.PBS__data';
    component.resourceSchema = { block_class_mro: 'PlayerCarPhysics__DataBlock', fields: [] };
    component.resourceData = spec();
    fixture.detectChanges();
  });

  it('summarizes the car', () => {
    const tile = (label: string) => component.tiles.find(t => t.label === label)!;
    expect(tile('Peak torque').value).toBe('235 N·m');
    expect(tile('Mass').value).toBe('1,405 kg');
    expect(tile('Top speed').value).toBe('270 km/h');
    expect(tile('Drivetrain').value).toBe('RWD');
    expect(tile('Drivetrain').sub).toContain('5-speed');
  });

  it('lists the used gears with their upshifts', () => {
    expect(component.gears.map(g => g.name)).toEqual(['R', 'N', '1st', '2nd', '3rd', '4th', '5th']);
    expect(component.gears.filter(g => g.upshift !== null).map(g => g.upshift)).toEqual([7900, 7900, 7900, 7900]);
    expect(component.gears[6].upshift).toBeNull();
    // 8000 rpm in 1st: 8000 / (128.46 * 3.07) m/s
    expect(component.gears[2].redlineSpeed).toBeCloseTo(73.03, 1);
  });

  it('writes a torque drag as one change of the table, with the rpm the game reads', () => {
    const points = component.torqueSeries[0].points.map(p => ({ ...p }));
    points[3] = { x: points[3].x, y: 260.4 };
    component.onTorqueChange({ seriesId: 'torque', points, changed: [3] });
    expect(appendChanges).toHaveBeenCalledTimes(1);
    const change = appendChanges.calls.mostRecent().args[0];
    expect(change.op).toBe('set');
    expect(change.id).toBe('ANSX.PBS__data/torques');
    expect(change.newValue[3]).toEqual({ rpm: 1600, torque: 260 });
    expect(change.newValue[4]).toEqual(change.oldValue[4]);
  });

  it('turns a dragged gear end into the ratio that reaches that speed at the redline', () => {
    const series = component.gearSeries.find(s => s.id === 'gear-4')!;
    const points = series.points.map(p => ({ ...p }));
    points[1] = { x: 200, y: 8000 };
    component.onGearChange({ seriesId: 'gear-4', points, changed: [1] });
    const change = appendChanges.calls.mostRecent().args[0];
    expect(change.id).toBe('ANSX.PBS__data/gear_ratios/4');
    expect(change.newValue).toBeCloseTo(8000 / (128.46 * (200 / 3.6)), 2);
  });

  it('writes grip values back as raw bytes', () => {
    const points = component.gripSeries[0].points.map(p => ({ ...p }));
    points[10] = { x: points[10].x, y: 0.5 };
    points[11] = { x: points[11].x, y: 9 };
    component.onGripChange({ seriesId: 'grip_table_f', points, changed: [10, 11] });
    const change = appendChanges.calls.mostRecent().args[0];
    expect(change.newValue[10]).toBe(64);
    expect(change.newValue[11]).toBe(255);
    expect(change.newValue[12]).toBe(100);
  });

  it('bundles the two brake force caps into one undo step', () => {
    const points = component.brakeSeries[0].points.map(p => ({ ...p }));
    points[0] = { ...points[0], y: 12 };
    points[1] = { ...points[1], y: 16 };
    component.onBrakeChange({ seriesId: 'brake_decel', points, changed: [0, 1] });
    const change = appendChanges.calls.mostRecent().args[0];
    expect(change.op).toBe('bundle');
    expect(change.changes.map((c: any) => c.id)).toEqual([
      'ANSX.PBS__data/max_brake_force_1',
      'ANSX.PBS__data/max_brake_force_2',
    ]);
  });

  it('copies one grip table onto the other', () => {
    component.copyGrip('grip_table_f');
    const change = appendChanges.calls.mostRecent().args[0];
    expect(change.id).toBe('ANSX.PBS__data/grip_table_r');
    expect(change.newValue.every((v: number) => v === 100)).toBeTrue();
  });

  describe('TNFS 3DO', () => {
    // ANSX.bigSpecsFam figures: no gear efficiency, one brake cap in m/s²
    const spec3do = () => {
      const d: { [key: string]: any } = {
        ...spec(),
        max_brake_force: 11.5,
        front_grip_mult: 1.796875,
        rear_grip_mult: 1.796875,
      };
      for (const key of ['max_brake_force_1', 'max_brake_force_2', 'gear_efficiency', 'thrust_scale']) delete d[key];
      return d;
    };

    beforeEach(() => {
      component.resourceId = 'ANSX.bigSpecsFam__data';
      component.resourceSchema = {
        block_class_mro: 'Tnfs3doCarPhysics__PlayerCarPhysics__DataBlock',
        fields: [],
      };
      component.resourceData = spec3do();
      fixture.detectChanges();
    });

    it('treats gear efficiency as 1', () => {
      expect(component.is3do).toBeTrue();
      expect(component.gears.every(g => g.efficiency === 1)).toBeTrue();
      expect(component.accelSeries[0].points.length).toBeGreaterThan(0);
    });

    it('edits the single brake cap as an acceleration', () => {
      expect(component.brakeSeries[0].points.map(p => p.y)).toEqual([11.5, 11.5]);
      const points = component.brakeSeries[0].points.map(p => ({ ...p }));
      points[0] = { ...points[0], y: 9.25 };
      component.onBrakeChange({ seriesId: 'brake_decel', points, changed: [0] });
      const change = appendChanges.calls.mostRecent().args[0];
      expect(change.id).toBe('ANSX.bigSpecsFam__data/max_brake_force');
      expect(change.newValue).toBe(9.25);
    });
  });
});
