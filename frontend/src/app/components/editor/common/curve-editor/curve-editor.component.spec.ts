import { NO_ERRORS_SCHEMA } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { CurveEditorComponent, CurveMarkerChange, CurveSeriesChange } from './curve-editor.component';

describe('CurveEditorComponent', () => {
  let fixture: ComponentFixture<CurveEditorComponent>;
  let component: CurveEditorComponent;
  let changes: CurveSeriesChange[];
  let markerChanges: CurveMarkerChange[];

  const pointer = (x: number, y: number) => {
    const r = component.svgRef.nativeElement.getBoundingClientRect();
    return {
      clientX: r.left + x,
      clientY: r.top + y,
      button: 0,
      pointerId: 1,
      target: component.svgRef.nativeElement,
      preventDefault: () => {},
    } as any;
  };
  const px = (axis: 'x' | 'y', v: number) => (component as any).toPx((component as any)[axis + 'Scale'], v);

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [CurveEditorComponent],
      schemas: [NO_ERRORS_SCHEMA],
    }).compileComponents();
    fixture = TestBed.createComponent(CurveEditorComponent);
    component = fixture.componentInstance;
    component.xAxis = { label: 'x', min: 0, max: 10 };
    component.yAxis = { label: 'y', min: 0, max: 100 };
    component.series = [
      {
        id: 'a',
        label: 'A',
        color: 'red',
        points: [0, 1, 2, 3, 4, 5].map(x => ({ x: x * 2, y: 50 })),
        editable: 'y',
        activeCount: 5,
        y: { min: 0, step: 1 },
      },
      {
        id: 'b',
        label: 'B',
        color: 'blue',
        points: [
          { x: 0, y: 10 },
          { x: 10, y: 10 },
        ],
      },
    ];
    component.markers = [{ id: 'm', value: 5, label: 'M', color: 'green', editable: true, constraints: { step: 0.5 } }];
    changes = [];
    markerChanges = [];
    component.seriesChange.subscribe(c => changes.push(c));
    component.markerChange.subscribe(c => markerChanges.push(c));
    fixture.detectChanges();
  });

  it('makes the first editable series the edited one', () => {
    expect(component.activeSeriesId).toBe('a');
    expect(component.isEditable).toBeTrue();
  });

  it('emits one change when a dragged point is released', () => {
    component.onPointerDown(pointer(px('x', 4), px('y', 50)));
    component.onPointerMove(pointer(px('x', 4), px('y', 70)));
    component.onPointerMove(pointer(px('x', 4), px('y', 80)));
    expect(changes.length).toBe(0);
    component.onPointerUp(pointer(px('x', 4), px('y', 80)));
    expect(changes.length).toBe(1);
    expect(changes[0].seriesId).toBe('a');
    expect(changes[0].changed).toEqual([2]);
    expect(changes[0].points[2].y).toBe(80);
    expect(changes[0].points[1].y).toBe(50);
  });

  it('emits nothing for a click without movement', () => {
    component.onPointerDown(pointer(px('x', 4), px('y', 50)));
    component.onPointerUp(pointer(px('x', 4), px('y', 50)));
    expect(changes.length).toBe(0);
    expect(component.selected).toEqual({ seriesId: 'a', index: 2 });
  });

  it('never edits the points past the active count', () => {
    component.onPointerDown(pointer(px('x', 10), px('y', 50)));
    component.onPointerMove(pointer(px('x', 10), px('y', 90)));
    component.onPointerUp(pointer(px('x', 10), px('y', 90)));
    expect(changes.length).toBe(0);
  });

  it('drags an editable marker', () => {
    component.onPointerDown(pointer(px('x', 5), px('y', 30)));
    component.onPointerMove(pointer(px('x', 7.1), px('y', 30)));
    component.onPointerUp(pointer(px('x', 7.1), px('y', 30)));
    expect(markerChanges).toEqual([{ markerId: 'm', value: 7 }]);
  });

  it('nudges the selected point with the arrow keys', () => {
    component.selected = { seriesId: 'a', index: 1 };
    component.onKeyDown(new KeyboardEvent('keydown', { key: 'ArrowUp', shiftKey: true }));
    expect(changes.length).toBe(1);
    expect(changes[0].points[1].y).toBe(60);
    component.onKeyDown(new KeyboardEvent('keydown', { key: 'ArrowRight' }));
    expect(component.selected).toEqual({ seriesId: 'a', index: 2 });
  });

  it('does not edit when disabled', () => {
    component.disabled = true;
    component.onPointerDown(pointer(px('x', 4), px('y', 50)));
    component.onPointerMove(pointer(px('x', 4), px('y', 80)));
    component.onPointerUp(pointer(px('x', 4), px('y', 80)));
    expect(changes.length).toBe(0);
  });
});
