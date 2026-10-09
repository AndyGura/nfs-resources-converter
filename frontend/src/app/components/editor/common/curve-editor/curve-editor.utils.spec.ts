import {
  applyDrawStroke,
  applyFalloffDrag,
  applySmoothBrush,
  decimalsForStep,
  falloffWeight,
  formatValue,
  nearestIndexByX,
  niceScale,
  snapValue,
} from './curve-editor.utils';

const line = (ys: number[]) => ys.map((y, x) => ({ x, y }));

describe('curve editor utils', () => {
  it('builds nice scales covering the range', () => {
    const s = niceScale(3, 97, 6);
    expect(s.min).toBe(0);
    expect(s.max).toBe(100);
    expect(s.step).toBe(20);
    expect(s.ticks).toEqual([0, 20, 40, 60, 80, 100]);
    const flat = niceScale(5, 5);
    expect(flat.min).toBeLessThan(5);
    expect(flat.max).toBeGreaterThan(5);
  });

  it('weights the falloff from 1 at the dragged point to 0 past the radius', () => {
    expect(falloffWeight(0, 0)).toBe(1);
    expect(falloffWeight(1, 0)).toBe(0);
    expect(falloffWeight(0, 3)).toBe(1);
    expect(falloffWeight(2, 3)).toBeGreaterThan(0);
    expect(falloffWeight(2, 3)).toBeLessThan(falloffWeight(1, 3));
    expect(falloffWeight(4, 3)).toBe(0);
  });

  it('snaps and clamps values', () => {
    expect(snapValue(1.26, { step: 0.25 })).toBe(1.25);
    expect(snapValue(-3, { min: 0 })).toBe(0);
    expect(snapValue(300, { max: 255, step: 1 })).toBe(255);
    expect(snapValue(1.234, undefined)).toBe(1.234);
  });

  it('finds the nearest point by x among the active ones', () => {
    const pts = line([0, 0, 0, 0, 0]);
    expect(nearestIndexByX(pts, 2.4)).toBe(2);
    expect(nearestIndexByX(pts, 2.6)).toBe(3);
    expect(nearestIndexByX(pts, 10, 3)).toBe(2);
    expect(nearestIndexByX([], 1)).toBe(-1);
  });

  it('drags a point with its neighbours by the falloff, within the active points', () => {
    const r = applyFalloffDrag(line([0, 0, 0, 0, 0, 0]), 2, 10, 2, 4, { step: 1 });
    expect(r.points.map(p => p.y)).toEqual([3, 8, 10, 8, 0, 0]);
    expect(r.changed).toEqual([0, 1, 2, 3]);
    const single = applyFalloffDrag(line([1, 1, 1]), 1, 2, 0, 3);
    expect(single.points.map(p => p.y)).toEqual([1, 3, 1]);
    expect(single.changed).toEqual([1]);
  });

  it('leaves values off the snapping grid alone when nothing moved', () => {
    const r = applyFalloffDrag(line([0.3, 0.3, 0.3]), 1, 0, 1, 3, { step: 1 });
    expect(r.changed).toEqual([]);
    expect(r.points.map(p => p.y)).toEqual([0.3, 0.3, 0.3]);
  });

  it('paints the points a freehand stroke crosses', () => {
    const pts = line([0, 0, 0, 0, 0, 0]);
    const changed = applyDrawStroke(pts, 1, 10, 3, 30, 5);
    expect(changed).toEqual([1, 2, 3]);
    expect(pts.map(p => p.y)).toEqual([0, 10, 20, 30, 0, 0]);
    // a stroke between two points still paints the nearest one
    const one = line([0, 0, 0]);
    expect(applyDrawStroke(one, 1.1, 5, 1.2, 5, 3)).toEqual([1]);
    // never past the active points
    const tail = line([0, 0, 0, 0]);
    applyDrawStroke(tail, 0, 1, 3, 1, 2);
    expect(tail.map(p => p.y)).toEqual([1, 1, 0, 0]);
  });

  it('smooths a spike under the brush', () => {
    const pts = line([0, 0, 0, 9, 0, 0, 0]);
    const changed = applySmoothBrush(pts, 3, 1, 1, 7);
    expect(changed).toContain(3);
    expect(pts[3].y).toBeLessThan(9);
    expect(pts[2].y).toBeGreaterThan(0);
    expect(pts[0].y).toBe(0);
  });

  it('formats values at the resolution of a step', () => {
    expect(decimalsForStep(1)).toBe(0);
    expect(decimalsForStep(0.25)).toBe(2);
    expect(decimalsForStep(2.5)).toBe(1);
    expect(decimalsForStep(0.1)).toBe(1);
    expect(formatValue(0.5, 2)).toBe('0.5');
    expect(formatValue(3, 2)).toBe('3');
    expect(formatValue(1250, 0)).toBe('1250');
  });
});
