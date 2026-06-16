import { ChangeDetectionStrategy, Component, ElementRef, EventEmitter, Input, Output, ViewChild } from '@angular/core';
import { PrimitiveGuiComponent } from '../../gui.component';
import { BehaviorSubject } from 'rxjs';

@Component({
  selector: 'app-binary-block-ui',
  templateUrl: './binary.block-ui.component.html',
  styleUrls: ['./binary.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  standalone: false,
})
// TODO optimize data changes, maybe it should not be a primitive gui component afterall
export class BinaryBlockUiComponent extends PrimitiveGuiComponent<number[]> {
  @ViewChild('editor') editorDiv?: ElementRef<HTMLDivElement>;

  override get resourceData(): number[] | undefined {
    return super.resourceData;
  }

  @Input()
  override set resourceData(value: number[] | undefined) {
    super.resourceData = value;
    if (value) {
      this.data$.next(new Uint8Array(value));
    } else {
      this.data$.next(this.empty);
    }
  }

  empty: Uint8Array = new Uint8Array();

  data$: BehaviorSubject<any> = new BehaviorSubject(new Uint8Array());

  onDataChange(arr: Uint8Array) {
    this.onValueSet(Array.from(arr));
  }
}
