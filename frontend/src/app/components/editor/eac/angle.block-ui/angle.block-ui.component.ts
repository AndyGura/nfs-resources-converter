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
import { Resource } from '../../types';
import { MainService } from '../../../../services/main.service';

@Component({
  selector: 'app-angle-block-ui',
  templateUrl: './angle.block-ui.component.html',
  styleUrls: ['./angle.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AngleBlockUiComponent implements GuiComponentInterface {
  @Input() resource: Resource | null = null;

  @Input()
  resourceDescription: string = '';

  @Output('changed') changed: EventEmitter<void> = new EventEmitter<void>();

  pi = Math.PI;

  dragging = false;

  @ViewChild('picker') picker?: ElementRef<HTMLDivElement>;

  @HostListener('mousedown', ['$event'])
  mousedown(event: MouseEvent) {
    this.dragging = true;
    this.updateRotation(event);
    this.onFocus();
  }

  @HostListener('mousemove', ['$event'])
  mousemove(event: MouseEvent) {
    if (this.dragging) {
      this.updateRotation(event);
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
    this.resource!.data = newAngle;
    this.changed.emit();
    this.cdr.markForCheck();
  }

  onFocus() {
    if (this.resource) {
      this.mainService.focusedResourceId$.next(this.resource.id);
    }
  }

  onBlur() {
    if (this.mainService.focusedResourceId$.getValue() === this.resource?.id) {
      this.mainService.focusedResourceId$.next(null);
    }
  }
}
