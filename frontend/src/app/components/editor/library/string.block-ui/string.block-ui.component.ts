import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { GuiComponentInterface } from '../../gui-component.interface';

@Component({
  selector: 'app-string-block-ui',
  templateUrl: './string.block-ui.component.html',
  styleUrls: ['./string.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class StringBlockUiComponent implements GuiComponentInterface {
  get resource(): Resource | null {
    return this._resource;
  }

  @Input() set resource(value: Resource | null) {
    this._resource = value;
    if (!isNaN(+this._resource?.schema.length)) {
      this.minLength = this.maxLength = +this._resource?.schema.length;
    }
  }
  private _resource: Resource | null = null;

  @Output('changed') changed: EventEmitter<void> = new EventEmitter<void>();

  minLength: number | null = null;
  maxLength: number | null = null;

  constructor() {}
}
