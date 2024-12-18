import { AfterViewInit, ChangeDetectionStrategy, Component, ElementRef, Input, OnDestroy } from '@angular/core';
import { BehaviorSubject, combineLatest, Observable, Subject } from 'rxjs';
import { map, takeUntil } from 'rxjs/operators';
import { Pnt3, Point2, Point3 } from '@gg-web-engine/core';

@Component({
  selector: 'app-tri-minimap',
  templateUrl: './minimap.component.html',
  styleUrls: ['./minimap.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MinimapComponent implements AfterViewInit, OnDestroy {
  _roadSpline$: BehaviorSubject<Point3[]> = new BehaviorSubject<Point3[]>([]);
  _pointer$: BehaviorSubject<Point2 | null> = new BehaviorSubject<Point2 | null>(null);

  @Input('roadSpline') set roadSpline(value: Point3[]) {
    this._roadSpline$.next(value);
  }

  @Input('pointer') set pointer(value: Point2 | null) {
    this._pointer$.next(value);
  }

  @Input() splineClosed: boolean = false;

  svgSize$: BehaviorSubject<Point2> = new BehaviorSubject({ x: 100, y: 100 });
  scalingSquare$: BehaviorSubject<{ x: number; y: number; width: number; height: number }> = new BehaviorSubject<{
    x: number;
    y: number;
    width: number;
    height: number;
  }>({ x: 0, y: 0, width: 100, height: 100 });
  mapPolyline$: BehaviorSubject<string> = new BehaviorSubject<string>('');
  mapPointer$: BehaviorSubject<Point2 | null> = new BehaviorSubject<Point2 | null>(null);

  get trackLength$(): Observable<number> {
    return this._roadSpline$.pipe(
      map((s) => {
        let ret = 0;
        for (let i = 1; i < s.length; i++) {
          ret += Pnt3.dist(s[i], s[i - 1]);
        }
        return ret;
      }),
    );
  }

  private readonly destroyed$: Subject<void> = new Subject<void>();

  constructor(private readonly ref: ElementRef) {
  }

  ngAfterViewInit() {
    this._roadSpline$
      .pipe(
        takeUntil(this.destroyed$),
        map((points: Point3[]) => {
          let minPoint: Point2 = { x: Number.MAX_SAFE_INTEGER, y: Number.MAX_SAFE_INTEGER };
          let maxPoint: Point2 = { x: Number.MIN_SAFE_INTEGER, y: Number.MIN_SAFE_INTEGER };
          points.forEach(p => {
            minPoint = { x: Math.min(minPoint.x, p.x), y: Math.min(minPoint.y, p.z) };
            maxPoint = { x: Math.max(maxPoint.x, p.x), y: Math.max(maxPoint.y, p.z) };
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

    combineLatest([this._roadSpline$, this.scalingSquare$, this.svgSize$])
      .pipe(
        takeUntil(this.destroyed$),
        map(([points, scalingSquare, svgSize]) => {
          const polygonToDraw: Point2[] = points.map(p => ({
            x: ((p.x - scalingSquare.x) * svgSize.x) / scalingSquare.width,
            y: ((scalingSquare.y - p.z) * svgSize.y) / scalingSquare.height + svgSize.y,
          }));
          if (this.splineClosed && polygonToDraw.length) {
            polygonToDraw.push(polygonToDraw[0]);
          }
          return polygonToDraw.map(v => Math.round(v.x) + ',' + Math.round(v.y)).join(' ');
        }),
      )
      .subscribe(this.mapPolyline$);

    combineLatest([this._pointer$, this.scalingSquare$.asObservable(), this.svgSize$])
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
}
