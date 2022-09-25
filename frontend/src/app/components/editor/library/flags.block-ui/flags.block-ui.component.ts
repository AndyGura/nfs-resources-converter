import { ChangeDetectionStrategy, Component } from '@angular/core';
import { GuiComponentInterface } from '../../gui-component.interface';
import { MatSelectionListChange } from '@angular/material/list';

@Component({
  selector: 'app-flags.block-ui',
  templateUrl: './flags.block-ui.component.html',
  styleUrls: ['./flags.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FlagsBlockUiComponent implements GuiComponentInterface {

  resourceData: ReadData | null = null;
  name: string = '';

  constructor() { }

  onSelection(event: MatSelectionListChange) {
    for (const option of event.options) {
      this.resourceData!.value[option.value] = option.selected;
    }
  }

}

