import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  EventEmitter,
  Input,
  OnDestroy,
  Output,
} from '@angular/core';
import { BehaviorSubject, combineLatest, fromEvent, Observable, Subject } from 'rxjs';
import { map, takeUntil } from 'rxjs/operators';
import { Pnt2, Pnt3, Point2, Point3 } from '@gg-web-engine/core';

type Projection = 'x' | 'nx' | 'y' | 'ny' | 'z' | 'nz';

@Component({
  selector: 'app-minimap',
  templateUrl: './minimap.component.html',
  styleUrls: ['./minimap.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MinimapComponent implements AfterViewInit, OnDestroy {
  _roadSpline$: BehaviorSubject<Point3[]> = new BehaviorSubject<Point3[]>([]);
  _pointer$: BehaviorSubject<Point3 | null> = new BehaviorSubject<Point3 | null>(null);
  _projection$: BehaviorSubject<Projection> = new BehaviorSubject<Projection>('nz');

  _roadSplineProjected$: BehaviorSubject<Point2[]> = new BehaviorSubject<Point2[]>([]);
  _pointerProjected$: BehaviorSubject<Point2> = new BehaviorSubject<Point2>(Pnt2.O);

  @Input('roadSpline') set roadSpline(value: Point3[]) {
    this._roadSpline$.next(value);
  }

  @Input('pointer') set pointer(value: Point3 | null) {
    this._pointer$.next(value);
  }

  @Input('projection') set projection(value: Projection) {
    this._projection$.next(value);
  }

  @Input() splineClosed: boolean = false;
  @Output() pointerChange = new EventEmitter<Point3>();

  svgSize$: BehaviorSubject<Point2> = new BehaviorSubject({ x: 100, y: 100 });
  scalingSquare$: BehaviorSubject<{ x: number; y: number; width: number; height: number }> = new BehaviorSubject<{
    x: number;
    y: number;
    width: number;
    height: number;
  }>({ x: 0, y: 0, width: 100, height: 100 });
  mapPolyline$: BehaviorSubject<string> = new BehaviorSubject<string>('');
  mapPointer$: BehaviorSubject<Point2 | null> = new BehaviorSubject<Point2 | null>(null);

  private isShiftPressed = false;

  get trackLength$(): Observable<number> {
    return this._roadSpline$.pipe(
      map(s => {
        let ret = 0;
        for (let i = 1; i < s.length; i++) {
          ret += Pnt3.dist(s[i], s[i - 1]);
        }
        return ret;
      }),
    );
  }

  private readonly destroyed$: Subject<void> = new Subject<void>();
  private isDragging = false;

  constructor(private readonly ref: ElementRef) {}

  private projectionKeys(): ['x' | 'y' | 'z', 'x' | 'y' | 'z', 'x' | 'y' | 'z', boolean] {
    switch (this._projection$.getValue()) {
      case 'nz':
        return ['x', 'y', 'z', false];
      case 'z':
        return ['x', 'y', 'z', true];
      case 'ny':
        return ['x', 'z', 'y', false];
      case 'y':
        return ['x', 'z', 'y', true];
      case 'nx':
        return ['y', 'z', 'x', false];
      case 'x':
        return ['y', 'z', 'x', true];
    }
  }

  private unproject(point: Point2, z: number): Point3 {
    let [xKey, yKey, zKey, invert] = this.projectionKeys();
    let out = { x: 0, y: 0, z: 0 };
    out[xKey] = point.x;
    out[yKey] = invert ? -point.y : point.y;
    out[zKey] = invert ? -z : z;
    return out;
  }

  private projectionZ(point: Point3): number {
    let [_, __, zKey, invert] = this.projectionKeys();
    return invert ? -point[zKey] : point[zKey];
  }

  private project(point: Point3): Point2 {
    let [xKey, yKey, _, invertY] = this.projectionKeys();
    return { x: point[xKey], y: invertY ? -point[yKey] : point[yKey] };
  }

  ngAfterViewInit() {
    fromEvent(window, 'keydown')
      .pipe(takeUntil(this.destroyed$))
      .subscribe(event => {
        if ((event as KeyboardEvent).key === 'Shift') {
          this.isShiftPressed = true;
        }
      });
    fromEvent(window, 'keyup')
      .pipe(takeUntil(this.destroyed$))
      .subscribe(event => {
        if ((event as KeyboardEvent).key === 'Shift') {
          this.isShiftPressed = false;
        }
      });
    combineLatest([this._roadSpline$, this._projection$])
      .pipe(takeUntil(this.destroyed$))
      .subscribe(([roadSpline, _]) => {
        this._roadSplineProjected$.next(roadSpline.map(p => this.project(p)));
      });
    combineLatest([this._pointer$, this._projection$])
      .pipe(takeUntil(this.destroyed$))
      .subscribe(([pointer, _]) => {
        this._pointerProjected$.next(this.project(pointer || Pnt3.O));
      });
    this._roadSplineProjected$
      .pipe(
        takeUntil(this.destroyed$),
        map((points: Point2[]) => {
          let minPoint: Point2 = { x: Number.MAX_SAFE_INTEGER, y: Number.MAX_SAFE_INTEGER };
          let maxPoint: Point2 = { x: Number.MIN_SAFE_INTEGER, y: Number.MIN_SAFE_INTEGER };
          points.forEach(p => {
            minPoint = { x: Math.min(minPoint.x, p.x), y: Math.min(minPoint.y, p.y) };
            maxPoint = { x: Math.max(maxPoint.x, p.x), y: Math.max(maxPoint.y, p.y) };
          });
          const roadActualSize: Point2 = { x: maxPoint.x - minPoint.x, y: maxPoint.y - minPoint.y };
          // +10% margins
          return {
            x: minPoint.x - roadActualSize.x * 0.1,
            y: minPoint.y - roadActualSize.y * 0.1,
            width: roadActualSize.x * 1.2,
            height: roadActualSize.y * 1.2,
          };
        }),
      )
      .subscribe(this.scalingSquare$);

    combineLatest([this._roadSplineProjected$, this.scalingSquare$, this.svgSize$])
      .pipe(
        takeUntil(this.destroyed$),
        map(([points, scalingSquare, svgSize]) => {
          const polygonToDraw: Point2[] = points.map(p => ({
            x: ((p.x - scalingSquare.x) * svgSize.x) / scalingSquare.width,
            y: ((scalingSquare.y - p.y) * svgSize.y) / scalingSquare.height + svgSize.y,
          }));
          if (this.splineClosed && polygonToDraw.length) {
            polygonToDraw.push(polygonToDraw[0]);
          }
          return polygonToDraw.map(v => Math.round(v.x) + ',' + Math.round(v.y)).join(' ');
        }),
      )
      .subscribe(this.mapPolyline$);

    combineLatest([this._pointerProjected$, this.scalingSquare$.asObservable(), this.svgSize$])
      .pipe(
        takeUntil(this.destroyed$),
        map(([point, scalingSquare, svgSize]) => {
          if (!point) {
            return null;
          }
          return {
            x: ((point.x - scalingSquare.x) * svgSize.x) / scalingSquare.width,
            y: ((scalingSquare.y - point.y) * svgSize.y) / scalingSquare.height + svgSize.y,
          };
        }),
      )
      .subscribe(this.mapPointer$);

    const updateSize = () => {
      this.svgSize$.next({ x: this.ref.nativeElement.clientWidth, y: this.ref.nativeElement.clientHeight });
    };
    new ResizeObserver(updateSize).observe(this.ref.nativeElement);
    updateSize();
  }

  ngOnDestroy(): void {
    this.destroyed$.next();
    this.destroyed$.complete();
  }

  startDrag(event: MouseEvent) {
    this.isDragging = true;
    this.updatePointer(event);
  }

  drag(event: MouseEvent) {
    if (this.isDragging) {
      this.updatePointer(event);
    }
  }

  endDrag() {
    this.isDragging = false;
  }

  private getClosestProjectedLineIndex(pos: Point2): [number, number] {
    const roadSplineProjected = this._roadSplineProjected$.getValue();
    let closestLineIndex = 0;
    let minDistance = Number.MAX_SAFE_INTEGER;
    for (let i = 1; i < roadSplineProjected.length; i++) {
      const p = roadSplineProjected[i - 1];
      const d = Pnt2.sub(roadSplineProjected[i], roadSplineProjected[i - 1]);
      const t = Math.max(0, Math.min(1, ((pos.x - p.x) * d.x + (pos.y - p.y) * d.y) / Pnt2.lenSq(d)));
      const projX = p.x + t * d.x;
      const projY = p.y + t * d.y;
      const distance = Math.hypot(pos.x - projX, pos.y - projY);
      if (distance < minDistance) {
        minDistance = distance;
        closestLineIndex = i - 1;
      }
    }
    const p1 = roadSplineProjected[closestLineIndex];
    const p2 = roadSplineProjected[closestLineIndex + 1];
    const d = Pnt2.sub(p2, p1);
    const t = Math.max(0, Math.min(1, ((pos.x - p1.x) * d.x + (pos.y - p1.y) * d.y) / Pnt2.lenSq(d)));
    return [closestLineIndex, t];
  }

  private getRoadSplineProjectionZ(pos: Point2): number {
    const [closestLineIndex, t] = this.getClosestProjectedLineIndex(pos);
    const roadSpline = this._roadSpline$.getValue();
    return (
      this.projectionZ(roadSpline[closestLineIndex]) +
      t * (this.projectionZ(roadSpline[closestLineIndex + 1]) - this.projectionZ(roadSpline[closestLineIndex]))
    );
  }

  private updatePointer(event: MouseEvent) {
    const boundingRect = this.ref.nativeElement.querySelector('svg')?.getBoundingClientRect();
    if (boundingRect) {
      const localPos = {
        x: event.clientX - boundingRect.left,
        y: boundingRect.height - event.clientY + boundingRect.top,
      };
      const scalingSquare = this.scalingSquare$.getValue();
      const svgSize = this.svgSize$.getValue();

      const oldPtr = this._pointerProjected$.getValue() || Pnt2.O;
      let newPtr = {
        x: localPos.x * (scalingSquare.width / svgSize.x) + scalingSquare.x,
        y: localPos.y * (scalingSquare.height / svgSize.y) + scalingSquare.y,
      };

      if (this.isShiftPressed) {
        const roadSplineProjected = this._roadSplineProjected$.getValue();
        const [oldClosestLineIndex, oldT] = this.getClosestProjectedLineIndex(oldPtr);
        const [newClosestLineIndex, newT] = this.getClosestProjectedLineIndex(newPtr);
        const oldOffsetVector = Pnt2.sub(
          oldPtr,
          Pnt2.lerp(roadSplineProjected[oldClosestLineIndex], roadSplineProjected[oldClosestLineIndex + 1], oldT),
        );
        newPtr = Pnt2.add(
          oldOffsetVector,
          Pnt2.lerp(roadSplineProjected[newClosestLineIndex], roadSplineProjected[newClosestLineIndex + 1], newT),
        );
      }
      const elevation = this.projectionZ(this._pointer$.getValue() || Pnt3.O) - this.getRoadSplineProjectionZ(oldPtr);
      this.pointerChange.emit(this.unproject(newPtr, elevation + this.getRoadSplineProjectionZ(newPtr)));
    }
  }
}
