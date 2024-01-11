import { ChangeDetectionStrategy, ChangeDetectorRef, Component, EventEmitter, Input, Output } from '@angular/core';
import { GuiComponentInterface } from '../../gui-component.interface';

@Component({
  selector: 'app-shpi-block-ui',
  templateUrl: './shpi.block-ui.component.html',
  styleUrls: ['./shpi.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ShpiBlockUiComponent implements GuiComponentInterface {
  @Input() resourceData: BlockData | null = null;
  name: string = '';

  @Output('changed') changed: EventEmitter<void> = new EventEmitter<void>();

  get resourcesMap(): { [key: string]: BlockData | ReadError } {
    const res: { [key: string]: BlockData | ReadError } = {};
    for (let i = 0; i < this.resourceData?.value.children_descriptions?.value.length; i++) {
      const name = this.resourceData?.value.children_descriptions?.value[i].value.name.value;
      res[name] = this.resourceData?.value.children?.value[i];
    }
    return res;
  }
}
