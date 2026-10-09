import { NO_ERRORS_SCHEMA } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { BehaviorSubject, Subject } from 'rxjs';
import { CarAiAndCrashBodyBlockUiComponent } from './car-ai-and-crash-body.block-ui.component';
import { MainService } from '../../../../services/main.service';
import { ChangesService } from '../../../../services/changes.service';

// ANSX.PDN figures
const pdn = () => ({
  half_width: 0.914,
  half_height: 0.6,
  half_length: 2.195,
  moment_of_inertia: 1.4,
  mass: 1,
  handling_factor: 0xa0000,
  speed_factor: 0.92,
  power_curve: Array.from({ length: 100 }, (_, i) => Math.max(0, 0.2 - i * 0.003)),
  top_speeds: [0, 20, 35.5, 50.2, 63.5, 74.7],
  max_rpm: 8000,
  gear_count: 5,
});

describe('CarAiAndCrashBodyBlockUiComponent', () => {
  let fixture: ComponentFixture<CarAiAndCrashBodyBlockUiComponent>;
  let component: CarAiAndCrashBodyBlockUiComponent;
  let appendChanges: jasmine.Spy;

  beforeEach(async () => {
    appendChanges = jasmine.createSpy('appendChanges').and.returnValue(Promise.resolve());
    await TestBed.configureTestingModule({
      declarations: [CarAiAndCrashBodyBlockUiComponent],
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
    fixture = TestBed.createComponent(CarAiAndCrashBodyBlockUiComponent);
    component = fixture.componentInstance;
    component.resourceId = 'ANSX.PDN__data';
    component.resourceSchema = { block_class_mro: 'CarAiAndCrashBody__DataBlock', fields: [] };
    component.resourceData = pdn();
    fixture.detectChanges();
  });

  it('makes the single-field tiles editable', () => {
    const editable = component.tiles.filter(t => t.edit).map(t => t.id);
    expect(editable).toEqual(['mass', 'top_speed', 'speed_factor', 'handling_factor', 'gear_count']);
    expect(component.tiles.find(t => t.id === 'handling_factor')!.edit!.value).toBe(14.06);
  });

  it('scales every gear top speed from the AI top speed tile, as one undo step', () => {
    component.onTileChange({ id: 'top_speed', value: 74.7 * 3.6 * 2 });
    const change = appendChanges.calls.mostRecent().args[0];
    expect(change.op).toBe('bundle');
    expect(change.changes.map((c: any) => c.newValue)).toEqual([40, 71, 100.4, 127, 149.4]);
  });

  it('writes the corner slowdown tile in degrees as a 24-bit angle', () => {
    component.onTileChange({ id: 'handling_factor', value: 20 });
    const change = appendChanges.calls.mostRecent().args[0];
    expect(change.id).toBe('ANSX.PDN__data/handling_factor');
    expect(change.newValue).toBe(Math.round((20 * 0x1000000) / 360));
  });

  it('has no editable top speed for a car without gears', () => {
    component.resourceData = { ...pdn(), top_speeds: [0, 0, 0, 0, 0, 0], handling_factor: 0xff0000 };
    expect(component.tiles.find(t => t.label === 'AI top speed')!.edit).toBeUndefined();
    expect(component.tiles.find(t => t.label === 'Corner slowdown')!.value).toBe('None');
  });
});
