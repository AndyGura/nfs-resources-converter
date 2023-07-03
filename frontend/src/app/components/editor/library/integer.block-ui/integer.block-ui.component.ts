import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { GuiComponentInterface } from '../../gui-component.interface';

@Component({
  selector: 'app-integer-block-ui',
  templateUrl: './integer.block-ui.component.html',
  styleUrls: ['./integer.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class IntegerBlockUiComponent implements GuiComponentInterface {
  @Input() resourceData: ReadData | null = null;
  name: string = '';

  @Output('changed') changed: EventEmitter<void> = new EventEmitter<void>();

  constructor() {}
}
