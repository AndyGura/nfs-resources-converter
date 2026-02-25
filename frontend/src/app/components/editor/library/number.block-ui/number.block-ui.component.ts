import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { GuiComponentInterface } from '../../gui-component.interface';
import { Resource } from '../../types';

@Component({
  selector: 'app-number-block-ui',
  templateUrl: './number.block-ui.component.html',
  styleUrls: ['./number.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class NumberBlockUiComponent implements GuiComponentInterface {
  @Input() resource: Resource | null = null;

  @Input()
  resourceDescription: string = '';

  @Input()
  disabled: boolean = false;

  @Output('changed') changed: EventEmitter<void> = new EventEmitter<void>();

  constructor() {}
}
