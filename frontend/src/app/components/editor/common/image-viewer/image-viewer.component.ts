import {
  AfterViewInit,
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  ElementRef,
  inject,
  Input,
  OnDestroy,
  ViewChild,
} from '@angular/core';
import { BehaviorSubject, debounceTime, filter, Subject, takeUntil } from 'rxjs';
import { MainService } from '../../../../services/main.service';
import { ChangesService } from '../../../../services/changes.service';
import { BlockData, BlockSchema } from '../../types';

@Component({
  selector: 'app-image-viewer',
  templateUrl: './image-viewer.component.html',
  styleUrls: ['./image-viewer.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  standalone: false,
})
export class ImageViewerComponent implements AfterViewInit, OnDestroy {
  private readonly mainService = inject(MainService);
  private readonly changes = inject(ChangesService);
  private readonly cdr = inject(ChangeDetectorRef);

  private _resourceId?: string;
  @Input()
  get resourceId(): string | undefined {
    return this._resourceId;
  }
  set resourceId(value: string | undefined) {
    if (this._resourceId === value) return;
    this._resourceId = value;
    this.imageNeedsUpdate$.next();
  }
  @Input() hideBlockActions = false;
  @Input() resourceName?: string;
  private _resourceData?: BlockData;
  @Input()
  get resourceData(): BlockData | undefined {
    return this._resourceData;
  }
  set resourceData(value: BlockData | undefined) {
    if (this._resourceData === value) return;
    this._resourceData = value;
    this.imageNeedsUpdate$.next();
  }
  @Input() resourceSchema?: BlockSchema;
  @Input() height = 'calc(60vh)';
  @Input() resourceDescription?: string;
  @Input() hideName = false;
  @Input() hideCustomActions = false;

  @Input() customStats?: { label: string; value: string }[];

  public imageNeedsUpdate$ = new Subject<void>();
  imageUrl$: BehaviorSubject<string | null> = new BehaviorSubject<string | null>(null);
  loading$: BehaviorSubject<boolean> = new BehaviorSubject<boolean>(false);
  imageWidth?: number;
  imageHeight?: number;

  @ViewChild('imageContainer') imageContainer?: ElementRef<HTMLDivElement>;

  private readonly destroyed$: Subject<void> = new Subject<void>();
  zoom = 100;

  isPanning = false;
  startX = 0;
  startY = 0;
  startScrollLeft = 0;
  startScrollTop = 0;

  get sliderValue(): number {
    return Math.log2(this.zoom / 100);
  }

  set sliderValue(value: number) {
    const oldZoom = this.zoom;
    this.zoom = Math.round(Math.pow(2, value) * 100);
    if (this.imageContainer) {
      const container = this.imageContainer.nativeElement;
      this.applyZoomAtAnchorDirect(this.zoom / oldZoom, container.clientWidth / 2, container.clientHeight / 2);
    } else {
      this.cdr.markForCheck();
    }
  }

  minZoomLog = Math.log2(10 / 100);
  maxZoomLog = Math.log2(1500 / 100);

  minZoom = 10;
  maxZoom = 1500;

  ngAfterViewInit() {
    this.imageNeedsUpdate$.pipe(takeUntil(this.destroyed$), debounceTime(20)).subscribe(() => {
      this.reload();
    });
    this.changes.change$
      .pipe(
        takeUntil(this.destroyed$),
        filter(x => !!(this.resourceId && x.startsWith(this.resourceId))),
      )
      .subscribe(() => {
        this.imageNeedsUpdate$.next();
      });
    this.imageNeedsUpdate$.next();
  }

  ngOnDestroy(): void {
    this.destroyed$.next();
    this.destroyed$.complete();
    this.imageNeedsUpdate$.complete();
  }

  reload() {
    this.imageUrl$.next(null);
    this.imageWidth = undefined;
    this.imageHeight = undefined;
    if (this.resourceId) {
      setTimeout(() => this.fitZoom(), 0);
      this.loading$.next(true);
      this.mainService.api
        .serializeResource(this.resourceId)
        .then(paths => {
          let url = paths.find(x => x.endsWith('.png'));
          if (!url) {
            this.imageUrl$.next(null);
          } else {
            this.imageUrl$.next(url + '?ts=' + Date.now());
          }
        })
        .catch(() => this.imageUrl$.next(null))
        .finally(() => {
          this.loading$.next(false);
          this.cdr.markForCheck();
        });
    }
  }

  onImageLoad(event: Event) {
    const img = event.target as HTMLImageElement;
    this.imageWidth = img.naturalWidth;
    this.imageHeight = img.naturalHeight;
    this.fitZoom();
    this.cdr.markForCheck();
  }

  zoomIn() {
    if (!this.imageContainer) {
      if (this.zoom < this.maxZoom) {
        this.zoom = Math.min(Math.ceil(this.zoom * 1.2), this.maxZoom);
        this.cdr.markForCheck();
      }
      return;
    }
    const container = this.imageContainer.nativeElement;
    this.applyZoomAtAnchor('in', container.clientWidth / 2, container.clientHeight / 2);
  }

  zoomOut() {
    if (!this.imageContainer) {
      if (this.zoom > this.minZoom) {
        this.zoom = Math.max(Math.floor(this.zoom / 1.2), this.minZoom);
        this.cdr.markForCheck();
      }
      return;
    }
    const container = this.imageContainer.nativeElement;
    this.applyZoomAtAnchor('out', container.clientWidth / 2, container.clientHeight / 2);
  }

  onWheel(event: WheelEvent) {
    if (!this.imageContainer) return;
    const container = this.imageContainer.nativeElement;
    const rect = container.getBoundingClientRect();
    const anchorX = event.clientX - rect.left;
    const anchorY = event.clientY - rect.top;
    this.applyZoomAtAnchor(event.deltaY < 0 ? 'in' : 'out', anchorX, anchorY);
    event.preventDefault();
  }

  private applyZoomAtAnchor(direction: 'in' | 'out', anchorX: number, anchorY: number) {
    const oldZoom = this.zoom;
    if (direction === 'in') {
      if (this.zoom < this.maxZoom) {
        this.zoom = Math.min(Math.ceil(this.zoom * 1.2), this.maxZoom);
      } else {
        return;
      }
    } else {
      if (this.zoom > this.minZoom) {
        this.zoom = Math.max(Math.floor(this.zoom / 1.2), this.minZoom);
      } else {
        return;
      }
    }
    this.applyZoomAtAnchorDirect(this.zoom / oldZoom, anchorX, anchorY);
  }

  private applyZoomAtAnchorDirect(zoomRatio: number, anchorX: number, anchorY: number) {
    if (!this.imageContainer || !this.resourceData) return;

    const container = this.imageContainer.nativeElement;
    const imgElement = container.querySelector('img, .image-placeholder');
    if (!imgElement) return;

    const scrollLeft = container.scrollLeft;
    const scrollTop = container.scrollTop;

    const imgRect = imgElement.getBoundingClientRect();
    const containerRect = container.getBoundingClientRect();

    const relativeX = anchorX + scrollLeft - (imgRect.left - containerRect.left + scrollLeft);
    const relativeY = anchorY + scrollTop - (imgRect.top - containerRect.top + scrollTop);

    const newRelativeX = relativeX * zoomRatio;
    const newRelativeY = relativeY * zoomRatio;

    this.cdr.markForCheck();

    requestAnimationFrame(() => {
      const newImgRect = imgElement.getBoundingClientRect();
      const newContainerRect = container.getBoundingClientRect();

      const imgOffsetLeft = newImgRect.left - newContainerRect.left + container.scrollLeft;
      const imgOffsetTop = newImgRect.top - newContainerRect.top + container.scrollTop;

      container.scrollLeft = newRelativeX + imgOffsetLeft - anchorX;
      container.scrollTop = newRelativeY + imgOffsetTop - anchorY;
    });
  }

  onMouseDown(event: MouseEvent) {
    if (!this.imageContainer) return;
    this.isPanning = true;
    this.startX = event.pageX - this.imageContainer.nativeElement.offsetLeft;
    this.startY = event.pageY - this.imageContainer.nativeElement.offsetTop;
    this.startScrollLeft = this.imageContainer.nativeElement.scrollLeft;
    this.startScrollTop = this.imageContainer.nativeElement.scrollTop;
    this.cdr.markForCheck();
  }

  onMouseMove(event: MouseEvent) {
    if (!this.isPanning || !this.imageContainer) return;
    event.preventDefault();
    const x = event.pageX - this.imageContainer.nativeElement.offsetLeft;
    const y = event.pageY - this.imageContainer.nativeElement.offsetTop;
    const walkX = x - this.startX;
    const walkY = y - this.startY;
    this.imageContainer.nativeElement.scrollLeft = this.startScrollLeft - walkX;
    this.imageContainer.nativeElement.scrollTop = this.startScrollTop - walkY;
  }

  onMouseUp() {
    this.isPanning = false;
    this.cdr.markForCheck();
  }

  onMouseLeave() {
    this.isPanning = false;
    this.cdr.markForCheck();
  }

  resetZoom() {
    this.zoom = 100;
    this.cdr.markForCheck();
  }

  fitZoom() {
    if (this.imageWidth && this.imageHeight && this.imageContainer) {
      const container = this.imageContainer.nativeElement;
      const availableWidth = container.clientWidth - 32;
      const availableHeight = container.clientHeight - 32;
      const zoomX = availableWidth / this.imageWidth;
      const zoomY = availableHeight / this.imageHeight;
      const idealZoom = Math.min(zoomX, zoomY);

      this.zoom = Math.floor(idealZoom * 100);

      if (this.zoom <= 0) {
        this.zoom = 100;
      }
      this.cdr.markForCheck();
    }
  }
}
