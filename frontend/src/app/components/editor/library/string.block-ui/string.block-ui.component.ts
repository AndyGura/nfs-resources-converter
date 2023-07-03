import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { GuiComponentInterface } from '../../gui-component.interface';

@Component({
  selector: 'app-string-block-ui',
  templateUrl: './string.block-ui.component.html',
  styleUrls: ['./string.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class StringBlockUiComponent implements GuiComponentInterface {
  @Input() resourceData: ReadData | null = null;
  name: string = '';

  @Output('changed') changed: EventEmitter<void> = new EventEmitter<void>();

  constructor() {}
}
