import { ChangeDetectionStrategy, Component, EventEmitter, Output } from '@angular/core';
import { GuiComponentInterface } from '../../gui-component.interface';

@Component({
  selector: 'app-enum.block-ui',
  templateUrl: './enum.block-ui.component.html',
  styleUrls: ['./enum.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EnumBlockUiComponent implements GuiComponentInterface {

  resourceData: ReadData | null = null;
  name: string = '';

  @Output('changed') changed: EventEmitter<void> = new EventEmitter<void>();

  constructor() { }

}

