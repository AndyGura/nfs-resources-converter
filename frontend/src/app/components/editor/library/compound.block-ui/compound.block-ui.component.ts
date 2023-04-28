import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { GuiComponentInterface } from '../../gui-component.interface';

@Component({
  selector: 'app-compound-block-ui',
  templateUrl: './compound.block-ui.component.html',
  styleUrls: ['./compound.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CompoundBlockUiComponent implements GuiComponentInterface {

  @Input() resourceData: ReadData | null = null;
  name: string = '';

  @Output('changed') changed: EventEmitter<void> = new EventEmitter<void>();

  get fieldKeys(): string[] {
    return Object.keys(this.resourceData?.value || {});
  }

  constructor() {
  }

}
