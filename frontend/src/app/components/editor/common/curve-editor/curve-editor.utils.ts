export type CurvePoint = { x: number; y: number };

export type NiceScale = { min: number; max: number; step: number; ticks: number[] };

// "Nice" axis bounds and ticks (1, 2, 2.5, 5 x 10^n steps) covering [min, max] with about `count` ticks
export function niceScale(min: number, max: number, count: number = 6): NiceScale {
  if (!isFinite(min) || !isFinite(max)) {
    min = 0;
    max = 1;
  }
  if (min > max) [min, max] = [max, min];
  if (max - min < 1e-12) {
    const pad = Math.abs(max) > 1e-12 ? Math.abs(max) * 0.1 : 1;
    min -= pad;
    max += pad;
  }
  const rough = (max - min) / Math.max(1, count - 1);
  const mag = Math.pow(10, Math.floor(Math.log10(rough)));
  const norm = rough / mag;
  const nice = norm <= 1 ? 1 : norm <= 2 ? 2 : norm <= 2.5 ? 2.5 : norm <= 5 ? 5 : 10;
  const step = nice * mag;
  const niceMin = Math.floor(min / step + 1e-9) * step;
  const niceMax = Math.ceil(max / step - 1e-9) * step;
  const ticks: number[] = [];
  for (let v = niceMin; v <= niceMax + step * 1e-6; v += step) {
    ticks.push(Math.abs(v) < step * 1e-9 ? 0 : v);
  }
  return { min: niceMin, max: niceMax, step, ticks };
}

// Weight of a neighbour `distance` points away from the dragged one: 1 at the dragged point, smooth (cosine) fall
// to 0 just past `radius`
export function falloffWeight(distance: number, radius: number): number {
  distance = Math.abs(distance);
  if (radius <= 0) return distance === 0 ? 1 : 0;
  if (distance > radius) return 0;
  return 0.5 * (1 + Math.cos((Math.PI * distance) / (radius + 1)));
}

export type ValueConstraints = { min?: number; max?: number; step?: number };

export function snapValue(value: number, c: ValueConstraints | undefined): number {
  if (!c) return value;
  if (c.step && c.step > 0) {
    value = Math.round(value / c.step) * c.step;
  }
  if (c.min !== undefined && value < c.min) value = c.min;
  if (c.max !== undefined && value > c.max) value = c.max;
  return value;
}

// Index of the point with the x closest to `x`, among the first `count` points sorted by x
export function nearestIndexByX(points: CurvePoint[], x: number, count: number = points.length): number {
  count = Math.min(count, points.length);
  if (count <= 0) return -1;
  let lo = 0;
  let hi = count - 1;
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1;
    if (points[mid].x < x) lo = mid;
    else hi = mid;
  }
  return Math.abs(points[lo].x - x) <= Math.abs(points[hi].x - x) ? lo : hi;
}

export type BrushResult = { points: CurvePoint[]; changed: number[] };

// Moves point `index` of `original` by `dy` and its neighbours by `dy` x falloff, `radius` points on each side.
// Only the first `activeCount` points are touched
export function applyFalloffDrag(
  original: CurvePoint[],
  index: number,
  dy: number,
  radius: number,
  activeCount: number,
  c?: ValueConstraints,
): BrushResult {
  const points = original.map(p => ({ ...p }));
  const changed: number[] = [];
  if (dy === 0) return { points, changed };
  const from = Math.max(0, index - radius);
  const to = Math.min(activeCount - 1, index + radius);
  for (let i = from; i <= to; i++) {
    const w = falloffWeight(i - index, radius);
    // points the falloff barely reaches keep their value instead of being snapped to the grid
    if (w <= 0 || Math.abs(dy * w) < (c?.step ?? 0) / 2) continue;
    const y = snapValue(original[i].y + dy * w, c);
    if (y !== original[i].y) {
      points[i].y = y;
      changed.push(i);
    }
  }
  return { points, changed };
}

// Freehand stroke from (x0, y0) to (x1, y1): every active point with x between x0 and x1 gets the y of the
// stroke at its x. Mutates `points`, returns the indices it changed
export function applyDrawStroke(
  points: CurvePoint[],
  x0: number,
  y0: number,
  x1: number,
  y1: number,
  activeCount: number,
  c?: ValueConstraints,
): number[] {
  const changed: number[] = [];
  const lo = Math.min(x0, x1);
  const hi = Math.max(x0, x1);
  const count = Math.min(activeCount, points.length);
  let start = nearestIndexByX(points, lo, count);
  if (start < 0) return changed;
  // the nearest point to a stroke covering no point's x at all still gets painted
  if (points[start].x < lo && start + 1 < count && points[start + 1].x <= hi) start++;
  let any = false;
  for (let i = start; i < count && (points[i].x <= hi || !any); i++) {
    any = true;
    const t = hi - lo < 1e-12 ? 1 : (points[i].x - x0) / (x1 - x0);
    const y = snapValue(y0 + (y1 - y0) * Math.min(1, Math.max(0, t)), c);
    if (y !== points[i].y) {
      points[i].y = y;
      changed.push(i);
    }
  }
  return changed;
}

// One pass of a smoothing brush centred on point `center`: each active point within `radius` moves towards the
// average of itself and its two neighbours, by `strength` x falloff. Mutates `points`, returns the changed indices
export function applySmoothBrush(
  points: CurvePoint[],
  center: number,
  radius: number,
  strength: number,
  activeCount: number,
  c?: ValueConstraints,
): number[] {
  const count = Math.min(activeCount, points.length);
  const from = Math.max(0, center - radius);
  const to = Math.min(count - 1, center + radius);
  const source = points.map(p => p.y);
  const changed: number[] = [];
  for (let i = from; i <= to; i++) {
    const prev = source[Math.max(0, i - 1)];
    const next = source[Math.min(count - 1, i + 1)];
    const target = (prev + source[i] + next) / 3;
    const w = falloffWeight(i - center, radius) * strength;
    const y = snapValue(source[i] + (target - source[i]) * w, c);
    if (y !== points[i].y) {
      points[i].y = y;
      changed.push(i);
    }
  }
  return changed;
}

// Digits after the decimal point that show a value at `step` resolution (0..6)
export function decimalsForStep(step: number | undefined): number {
  if (!step || step <= 0) return 3;
  for (let d = 0; d < 6; d++) {
    const scaled = step * Math.pow(10, d);
    if (Math.abs(scaled - Math.round(scaled)) < 1e-6 * Math.max(1, scaled)) return d;
  }
  return 6;
}

export function formatValue(value: number, decimals: number): string {
  if (!isFinite(value)) return '' + value;
  const fixed = value.toFixed(decimals);
  return decimals > 0 ? fixed.replace(/\.?0+$/, '') : fixed;
}
