import { ChangeDetectionStrategy, Component, ElementRef, EventEmitter, Input, Output, ViewChild } from '@angular/core';
import { GuiComponentInterface } from '../../gui-component.interface';
import { BehaviorSubject } from 'rxjs';
import { Resource } from '../../types';

@Component({
  selector: 'app-binary-block-ui',
  templateUrl: './binary.block-ui.component.html',
  styleUrls: ['./binary.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BinaryBlockUiComponent implements GuiComponentInterface {
  @ViewChild('editor') editorDiv?: ElementRef<HTMLDivElement>;

  private _resource: Resource | null = null;
  get resource(): Resource | null {
    return this._resource;
  }

  @Input()
  set resource(value: Resource | null) {
    this._resource = value;
    this.data$.next(new Uint8Array(value ? value.data : 0));
  }

  empty: Uint8Array = new Uint8Array();

  data$: BehaviorSubject<Uint8Array> = new BehaviorSubject(new Uint8Array());

  @Input()
  resourceDescription: string = '';

  @Input() disabled: boolean = false;

  @Output('changed') changed: EventEmitter<void> = new EventEmitter<void>();

  constructor() {}

  onDataChange(arr: Uint8Array) {
    this._resource!.data = Array.from(arr);
    this.changed.emit();
  }
}
