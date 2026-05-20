import { ChangeDetectionStrategy, Component, ElementRef, EventEmitter, Input, Output, ViewChild } from '@angular/core';
import { GuiComponentInterface } from '../../gui-component.interface';
import { BehaviorSubject } from 'rxjs';
import { BlockSchema } from '../../types';
import { MainService } from '../../../../services/main.service';

@Component({
  selector: 'app-binary-block-ui',
  templateUrl: './binary.block-ui.component.html',
  styleUrls: ['./binary.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BinaryBlockUiComponent implements GuiComponentInterface {
  @ViewChild('editor') editorDiv?: ElementRef<HTMLDivElement>;

  @Input() resourceId?: string;
  @Input() resourceName?: string;
  @Input() resourceSchema?: BlockSchema;
  private _resourceData?: number[];
  get resourceData(): number[] | undefined {
    return this._resourceData;
  }
  @Input()
  set resourceData(value: number[] | undefined) {
    this._resourceData = value;
    if (value) {
      this.data$.next(new Uint8Array(value));
    } else {
      this.data$.next(this.empty);
    }
  }

  @Input() resourceDescription?: string;

  @Input() hideName?: boolean;
  @Input() hideBlockActions?: boolean;
  @Input() disabled?: boolean;

  @Output('changed') changed: EventEmitter<number[]> = new EventEmitter<number[]>();

  empty: Uint8Array = new Uint8Array();

  data$: BehaviorSubject<Uint8Array> = new BehaviorSubject(new Uint8Array());

  constructor(private mainService: MainService) {}

  onDataChange(arr: Uint8Array) {
    this.changed.emit(Array.from(arr));
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
