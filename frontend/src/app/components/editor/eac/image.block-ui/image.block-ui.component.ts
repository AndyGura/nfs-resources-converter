import {
  AfterViewInit,
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  ElementRef,
  EventEmitter,
  Input,
  OnDestroy,
  Output,
  ViewChild,
} from '@angular/core';
import { GuiComponentInterface } from '../../gui-component.interface';
import { BehaviorSubject, Subject, takeUntil } from 'rxjs';
import { MainService } from '../../../../services/main.service';
import { CustomAction, Resource } from '../../types';
import { CustomActionService } from '../../../../services/custom-action.service';

@Component({
  selector: 'image-block-ui',
  templateUrl: './image.block-ui.component.html',
  styleUrls: ['./image.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ImageBlockUiComponent implements GuiComponentInterface, AfterViewInit, OnDestroy {
  _resource$: BehaviorSubject<Resource | null> = new BehaviorSubject<Resource | null>(null);
  imageUrl$: BehaviorSubject<string | null> = new BehaviorSubject<string | null>(null);

  @Input() set resource(value: Resource | null) {
    this._resource$.next(value);
  }

  get resource(): Resource | null {
    return this._resource$.getValue();
  }

  @Input() resourceDescription: string = '';

  @Input() hideName: boolean = false;

  @Input() hideBlockActions: boolean = false;

  @ViewChild('imageContainer') imageContainer?: ElementRef<HTMLDivElement>;
  @ViewChild('formatSelect') formatSelect?: any;

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

  @Output('changed') changed: EventEmitter<void> = new EventEmitter<void>();

  constructor(
    public readonly main: MainService,
    private readonly cdr: ChangeDetectorRef,
    private readonly customActionService: CustomActionService,
  ) {}

  async ngAfterViewInit() {
    this._resource$.pipe(takeUntil(this.destroyed$)).subscribe(async res => {
      if (res) {
        this.imageUrl$.next(null);
        setTimeout(() => this.fitZoom(), 0);
        const paths = await this.main.api.serializeResource(res.id);
        let url = paths.find(x => x.endsWith('.png'));
        if (!url) {
          this.imageUrl$.next(null);
        } else {
          this.imageUrl$.next(url + '?ts=' + Date.now());
        }
      } else {
        this.imageUrl$.next(null);
      }
    });

    this.imageUrl$.pipe(takeUntil(this.destroyed$)).subscribe(url => {
      this.cdr.markForCheck();
    });
  }

  ngOnDestroy(): void {
    this.destroyed$.next();
    this.destroyed$.complete();
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
    if (!this.imageContainer || !this.resource?.data) return;

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
    if (this.resource?.data?.width && this.imageContainer) {
      const container = this.imageContainer.nativeElement;
      const availableWidth = container.clientWidth - 32;
      const availableHeight = container.clientHeight - 32;
      const zoomX = availableWidth / this.resource.data.width;
      const zoomY = availableHeight / this.resource.data.height;
      const idealZoom = Math.min(zoomX, zoomY);

      this.zoom = Math.floor(idealZoom * 100);

      if (this.zoom <= 0) {
        this.zoom = 100;
      }
      this.cdr.markForCheck();
    }
  }

  customActionSimplifiedFormat(resourceId: string): 'rgba' | '4bit' | '8bit' {
    if (resourceId.startsWith('4Bit')) {
      return '4bit';
    } else if (resourceId === '8Bit') {
      return '8bit';
    } else {
      return 'rgba';
    }
  }

  async onFormatChange(newFormat: string) {
    if (!this.resource) return;
    const currentFormatSmpl = this.customActionSimplifiedFormat(this.resource.data.resource_id);
    const newFormatSmpl = this.customActionSimplifiedFormat(newFormat);
    if (newFormatSmpl === currentFormatSmpl) {
      this.resource.data.resource_id = newFormat;
      this.changed.next();
      return;
    }
    const action = this.resource.schema.custom_actions.find(
      (a: CustomAction) => a.method === 'convert_to_' + newFormatSmpl,
    );
    if (action) {
      const success = await this.customActionService.runCustomAction(this.resource, action);
      if (!success && this.formatSelect) {
        // restore value in dropdown
        this.formatSelect.control.setValue(this.resource.data.resource_id, { emitEvent: false });
        this.cdr.markForCheck();
      }
    } else {
      if (this.formatSelect) {
        this.formatSelect.control.setValue(this.resource.data.resource_id, { emitEvent: false });
      }
      this.cdr.markForCheck();
    }
  }
}
