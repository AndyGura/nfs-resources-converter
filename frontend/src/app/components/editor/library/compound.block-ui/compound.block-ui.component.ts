import { ChangeDetectionStrategy, Component, OnInit } from '@angular/core';
import { GuiComponentInterface } from '../../gui-component.interface';

@Component({
  selector: 'app-compound.block-ui',
  templateUrl: './compound.block-ui.component.html',
  styleUrls: ['./compound.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CompoundBlockUiComponent implements GuiComponentInterface {

  resourceData: ReadData | null = null;
  name: string = '';

  constructor() { }

}
