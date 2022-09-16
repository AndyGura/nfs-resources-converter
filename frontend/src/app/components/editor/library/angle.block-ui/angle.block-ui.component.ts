import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  ElementRef,
  HostListener,
  ViewChild
} from '@angular/core';
import { GuiComponentInterface } from '../../gui-component.interface';

@Component({
  selector: 'app-angle.block-ui',
  templateUrl: './angle.block-ui.component.html',
  styleUrls: ['./angle.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AngleBlockUiComponent implements GuiComponentInterface {

  resourceData: ReadData | null = null;
  name: string = '';

  pi = Math.PI;

  dragging = false;

  @ViewChild('picker') picker?: ElementRef<HTMLDivElement>;

  @HostListener('mousedown', ['$event'])
  mousedown(event: MouseEvent) {
    this.dragging = true;
    this.updateRotation(event);
  }

  @HostListener('mousemove', ['$event'])
  mousemove(event: MouseEvent) {
    if (this.dragging) {
      this.updateRotation(event);
    }
  }

  @HostListener('mouseup')
  @HostListener('mouseleave')
  mouseout() {
    this.dragging = false;
  }

  constructor(private readonly cdr: ChangeDetectorRef) { }

  private updateRotation(mouseEvent: MouseEvent) {
    const rect = this.picker!.nativeElement.getBoundingClientRect();
    let newAngle = Math.atan2(mouseEvent.clientY - rect.top - rect.height/2, mouseEvent.clientX - rect.left - rect.width / 2);
    if (mouseEvent.shiftKey) {
      newAngle = (Math.round( (newAngle * 180 / Math.PI)/ 15) * 15) * Math.PI / 180;
    }
    this.resourceData!.value = newAngle;
    this.cdr.markForCheck();
  }

}
