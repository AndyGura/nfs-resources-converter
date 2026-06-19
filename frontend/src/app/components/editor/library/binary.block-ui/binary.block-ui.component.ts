import { ChangeDetectionStrategy, Component, ElementRef, Input, ViewChild } from '@angular/core';
import { SubscribableGuiComponent } from '../../gui.component';
import { BehaviorSubject } from 'rxjs';
import { HexEditorDeltaChange } from 'ngx-hex-editor';

@Component({
  selector: 'app-binary-block-ui',
  templateUrl: './binary.block-ui.component.html',
  styleUrls: ['./binary.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  standalone: false,
})
export class BinaryBlockUiComponent extends SubscribableGuiComponent<number[]> {
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

  override onExternalChanges() {
    this.data$.next(new Uint8Array(super.resourceData!));
  }

  onDataChange(event: HexEditorDeltaChange) {
    let oldPart: number[] = [];
    let newPart: number[] = [];
    let index = event.index;
    switch (event.type) {
      case 'update':
        oldPart = [this.resourceData![event.index]];
        newPart = [event.data![0]];
        break;
      case 'insert':
        oldPart = [];
        if (index > this.resourceData!.length) {
          newPart = new Array(index - this.resourceData!.length).fill(0);
          newPart.push(event.data![0]);
          index = this.resourceData!.length;
        } else {
          newPart = [event.data![0]];
        }
        break;
      case 'delete':
        oldPart = Array.from(this.resourceData!.slice(event.index, event.index + event.count!));
        newPart = [];
        break;
      default:
        throw new Error('Unsupported hex editor event type ' + event.type);
    }
    this.emitNewChange({
      op: 'binary_delta',
      index,
      oldPart,
      newPart,
    });
  }
}
