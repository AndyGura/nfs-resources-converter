import { AfterViewInit, ChangeDetectionStrategy, Component, ElementRef, inject, Input, ViewChild } from '@angular/core';
import { SubscribableGuiComponent } from '../../gui.component';
import { BehaviorSubject, debounceTime, filter, Subject, takeUntil } from 'rxjs';
import { BlockData, CustomAction } from '../../types';
import { CustomActionService } from '../../../../services/custom-action.service';
import { MatSelectChange } from '@angular/material/select';

@Component({
  selector: 'image-block-ui',
  templateUrl: './image.block-ui.component.html',
  styleUrls: ['./image.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  standalone: false,
})
export class ImageBlockUiComponent extends SubscribableGuiComponent implements AfterViewInit {
  imageNeedsUpdate$ = new Subject<void>();
  imageUrl$: BehaviorSubject<string | null> = new BehaviorSubject<string | null>(null);
  loading$: BehaviorSubject<boolean> = new BehaviorSubject<boolean>(false);

  override get resourceId(): string | undefined {
    return super.resourceId;
  }

  @Input()
  override set resourceId(value: string | undefined) {
    if (super.resourceId === value) return;
    super.resourceId = value;
    this.imageNeedsUpdate$.next();
  }

  override get resourceData(): BlockData {
    return super.resourceData;
  }

  @Input()
  override set resourceData(value: BlockData) {
    if (value === super.resourceData) return;
    super.resourceData = value;
    this.imageNeedsUpdate$.next();
  }

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

  readonly customActionService = inject(CustomActionService);

  async ngAfterViewInit() {
    this.imageNeedsUpdate$.pipe(takeUntil(this.destroyed$), debounceTime(20)).subscribe(() => {
      this.imageUrl$.next(null);
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
          .finally(() => this.loading$.next(false));
      }
    });
    this.changes.change$
      .pipe(
        takeUntil(this.destroyed$),
        filter(x => !!((this.resourceId && x.startsWith(this.resourceId)) || x.includes('colors/data'))),
      )
      .subscribe(() => {
        this.imageNeedsUpdate$.next();
      });
    this.imageNeedsUpdate$.next();
  }

  override ngOnDestroy(): void {
    super.ngOnDestroy();
    this.destroyed$.next();
    this.destroyed$.complete();
    this.imageNeedsUpdate$.complete();
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
    if (!this.imageContainer || !this._resourceData) return;

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
    if (this._resourceData?.width && this.imageContainer) {
      const container = this.imageContainer.nativeElement;
      const availableWidth = container.clientWidth - 32;
      const availableHeight = container.clientHeight - 32;
      const zoomX = availableWidth / this._resourceData.width;
      const zoomY = availableHeight / this._resourceData.height;
      const idealZoom = Math.min(zoomX, zoomY);

      this.zoom = Math.floor(idealZoom * 100);

      if (this.zoom <= 0) {
        this.zoom = 100;
      }
      this.cdr.markForCheck();
    }
  }

  async onFormatChange(event: MatSelectChange) {
    const newFormat = event.value;
    if (!this._resourceData || this._resourceData.resource_id === newFormat) return;

    const customActionSimplifiedFormat = (resourceId: string): 'rgba' | '4bit' | '8bit' => {
      if (resourceId.startsWith('4Bit')) {
        return '4bit';
      } else if (resourceId === '8Bit') {
        return '8bit';
      } else {
        return 'rgba';
      }
    };
    const currentFormatSmpl = customActionSimplifiedFormat(this._resourceData.resource_id);
    const newFormatSmpl = customActionSimplifiedFormat(newFormat);

    const action = this.resourceSchema.custom_actions.find(
      (a: CustomAction) => a.method === 'convert_to_' + newFormatSmpl,
    )!;
    const formPatch: any = {};
    if (newFormatSmpl === 'rgba') {
      if (currentFormatSmpl === 'rgba') {
        formPatch['output_colors'] = 'use palette'; // this variable is unused when converting rgba -> rgba
      }
      formPatch['color_mode'] = newFormat;
    }
    if (newFormatSmpl === '8bit' && currentFormatSmpl === '4bit') {
      formPatch['channel'] = ''; // this variable is unused when converting 4bit -> 8bit
    }
    if (newFormatSmpl === '4bit') {
      formPatch['mode'] = newFormat;
      if (currentFormatSmpl === '8bit' || currentFormatSmpl === '4bit') {
        formPatch['channel'] = ''; // this variable is unused when converting 8bit -> 4bit
      }
    }
    const done = await this.customActionService.runCustomAction(
      this.resourceId!,
      this.resourceName!,
      action,
      formPatch,
      true,
    );
    if (!done) {
      // restore value in the input
      event.source.value = this.resourceData.resource_id;
    }
  }
}
