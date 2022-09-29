import { ChangeDetectionStrategy, Component, EventEmitter, Output } from '@angular/core';
import { GuiComponentInterface } from '../../gui-component.interface';

@Component({
  selector: 'app-fallback.block-ui',
  templateUrl: './fallback.block-ui.component.html',
  styleUrls: ['./fallback.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FallbackBlockUiComponent implements GuiComponentInterface {

  resourceData: ReadData | null = null;
  name: string = '';

  @Output('changed') changed: EventEmitter<void> = new EventEmitter<void>();

  constructor() {
  }

}
