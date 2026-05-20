import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  ElementRef,
  EventEmitter,
  HostListener,
  Input,
  Output,
  ViewChild,
} from '@angular/core';
import { GuiComponentInterface } from '../../gui-component.interface';
import { BlockSchema } from '../../types';
import { MainService } from '../../../../services/main.service';

@Component({
  selector: 'app-angle-block-ui',
  templateUrl: './angle.block-ui.component.html',
  styleUrls: ['./angle.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AngleBlockUiComponent implements GuiComponentInterface {
  @Input() resourceId?: string;
  @Input() resourceName?: string;
  @Input() resourceSchema?: BlockSchema;
  @Input() resourceData?: number;
  @Input() resourceDescription?: string;

  @Input() hideName?: boolean;
  @Input() hideBlockActions?: boolean;
  @Input() disabled?: boolean;

  @Output('changed') changed: EventEmitter<number> = new EventEmitter<number>();

  pi = Math.PI;

  dragging = false;

  @ViewChild('picker') picker?: ElementRef<HTMLDivElement>;

  @HostListener('mousedown', ['$event'])
  mousedown(event: MouseEvent) {
    if (this.disabled) return;
    this.dragging = true;
    this.updateRotation(event);
    this.onFocus();
  }

  @HostListener('mousemove', ['$event'])
  mousemove(event: MouseEvent) {
    if (this.dragging) {
      if (this.disabled) {
        this.dragging = false;
        this.onBlur();
      } else {
        this.updateRotation(event);
      }
    }
  }

  @HostListener('mouseup')
  mouseout() {
    this.dragging = false;
    this.onBlur();
  }

  @HostListener('mouseleave')
  mouseleave() {
    this.dragging = false;
    this.onBlur();
  }

  constructor(private readonly cdr: ChangeDetectorRef, private mainService: MainService) {}

  private updateRotation(mouseEvent: MouseEvent) {
    const rect = this.picker!.nativeElement.getBoundingClientRect();
    let newAngle = Math.atan2(
      mouseEvent.clientY - rect.top - rect.height / 2,
      mouseEvent.clientX - rect.left - rect.width / 2,
    );
    if (mouseEvent.shiftKey) {
      newAngle = (Math.round((newAngle * 180) / Math.PI / 15) * 15 * Math.PI) / 180;
    }
    this.resourceData = newAngle;
    this.changed.emit(newAngle);
    this.cdr.markForCheck();
  }

  onFocus() {
    if (this.resourceId) {
      this.mainService.focusedResourceId$.next(this.resourceId);
    }
  }

  onBlur() {
    if (this.mainService.focusedResourceId$.getValue() === this.resourceId) {
      this.mainService.focusedResourceId$.next(null);
    }
  }
}
