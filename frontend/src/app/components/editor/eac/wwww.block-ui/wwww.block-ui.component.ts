import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { GuiComponentInterface } from '../../gui-component.interface';

@Component({
  selector: 'app-wwww-block-ui',
  templateUrl: './wwww.block-ui.component.html',
  styleUrls: ['./wwww.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class WwwwBlockUiComponent implements GuiComponentInterface {
  @Input() resourceData: BlockData | null = null;
  name: string = '';

  @Output('changed') changed: EventEmitter<void> = new EventEmitter<void>();

  get resourcesMap(): { [key: string]: BlockData | ReadError } {
    const res: { [key: string]: BlockData | ReadError } = {};
    for (let i = 0; i < this.resourceData?.value.children?.value.length; i++) {
      res[i.toString()] = this.resourceData?.value.children?.value[i];
    }
    return res;
  }
}
