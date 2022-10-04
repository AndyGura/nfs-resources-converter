import { ChangeDetectionStrategy, Component, EventEmitter, Output } from '@angular/core';
import { GuiComponentInterface } from '../../gui-component.interface';

@Component({
  selector: 'app-wwww.block-ui',
  templateUrl: './wwww.block-ui.component.html',
  styleUrls: ['./wwww.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class WwwwBlockUiComponent implements GuiComponentInterface {

  resourceData: ReadData | null = null;
  name: string = '';

  @Output('changed') changed: EventEmitter<void> = new EventEmitter<void>();

  get resourcesMap(): { [key: string]: ReadData | ReadError } {
    const res: { [key: string]: ReadData | ReadError } = {};
    for (let i = 0; i < this.resourceData?.value.children?.value.length; i++) {
      res[i.toString()] = this.resourceData?.value.children?.value[i];
    }
    return res;
  };

}
