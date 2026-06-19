import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  ElementRef,
  HostListener,
  ViewChild,
} from '@angular/core';
import { PrimitiveGuiComponent } from '../../gui.component';

@Component({
  selector: 'app-angle-block-ui',
  templateUrl: './angle.block-ui.component.html',
  styleUrls: ['./angle.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  standalone: false,
})
// FIXME outputs change on each mouse move, should emit on mouseup
export class AngleBlockUiComponent extends PrimitiveGuiComponent<number> {
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

  constructor(readonly cdr: ChangeDetectorRef) {
    super();
  }

  private updateRotation(mouseEvent: MouseEvent) {
    const rect = this.picker!.nativeElement.getBoundingClientRect();
    let newAngle = Math.atan2(
      mouseEvent.clientY - rect.top - rect.height / 2,
      mouseEvent.clientX - rect.left - rect.width / 2,
    );
    if (mouseEvent.shiftKey) {
      newAngle = (Math.round((newAngle * 180) / Math.PI / 15) * 15 * Math.PI) / 180;
    }
    this.onValueSet(newAngle);
    this.cdr.markForCheck();
  }
}
