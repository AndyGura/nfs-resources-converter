import { NO_ERRORS_SCHEMA } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { BehaviorSubject } from 'rxjs';
import { AngleBlockUiComponent } from './angle.block-ui.component';
import { MainService } from '../../../../services/main.service';
import { ChangesService } from '../../../../services/changes.service';

describe('AngleBlockUiComponent', () => {
  let fixture: ComponentFixture<AngleBlockUiComponent>;
  let component: AngleBlockUiComponent;
  let appendChanges: jasmine.Spy;

  beforeEach(async () => {
    appendChanges = jasmine.createSpy('appendChanges').and.returnValue(Promise.resolve());
    await TestBed.configureTestingModule({
      declarations: [AngleBlockUiComponent],
      providers: [
        { provide: MainService, useValue: { focusedResourceId$: new BehaviorSubject(null) } },
        { provide: ChangesService, useValue: { appendChanges } },
      ],
      schemas: [NO_ERRORS_SCHEMA],
    }).compileComponents();
    AngleBlockUiComponent.unit$.next('deg');
    fixture = TestBed.createComponent(AngleBlockUiComponent);
    component = fixture.componentInstance;
    component.resourceId = 'f__data/angle';
  });

  it('shows radians data in degrees and writes radians back', () => {
    component.resourceSchema = { block_class_mro: 'Nfs1Angle8__AngleBlock__IntegerBlock__DataBlock' };
    component.resourceData = Math.PI / 2;
    expect(component.displayValue).toBe(90);
    component.onInput('180');
    expect(appendChanges.calls.mostRecent().args[0].newValue).toBeCloseTo(Math.PI, 10);
  });

  it('keeps an integer angle an integer', () => {
    component.resourceSchema = {
      block_class_mro: 'IntegerAngleBlock__IntegerBlock__DataBlock',
      angle_full_turn: 0x1000000,
    };
    component.resourceData = 0xa0000;
    expect(component.displayValue).toBe(14.063);
    component.onInput('20');
    expect(appendChanges.calls.mostRecent().args[0].newValue).toBe(Math.round((20 * 0x1000000) / 360));
  });

  it('switches every angle field to radians', () => {
    component.resourceSchema = { block_class_mro: 'Nfs1Angle8__AngleBlock__IntegerBlock__DataBlock' };
    component.resourceData = Math.PI;
    component.toggleUnit();
    expect(component.unit).toBe('rad');
    expect(component.displayValue).toBe(3.14159);
    component.toggleUnit();
  });

  it('does not write an unchanged value', () => {
    component.resourceSchema = {
      block_class_mro: 'IntegerAngleBlock__IntegerBlock__DataBlock',
      angle_full_turn: 0x1000000,
    };
    component.resourceData = 0x400000;
    component.onInput('90');
    expect(appendChanges).not.toHaveBeenCalled();
  });
});
