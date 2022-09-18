import { ChangeDetectionStrategy, Component } from '@angular/core';
import { GuiComponentInterface } from '../../gui-component.interface';

@Component({
  selector: 'app-shpi.block-ui',
  templateUrl: './shpi.block-ui.component.html',
  styleUrls: ['./shpi.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ShpiBlockUiComponent implements GuiComponentInterface {

  resourceData: ReadData | null = null;
  name: string = '';

  get resourcesMap(): { [key: string]: ReadData | ReadError } {
    const res: { [key: string]: ReadData | ReadError } = {};
    for (let i = 0; i < this.resourceData?.value.children_descriptions?.value.length; i++) {
      const name = this.resourceData?.value.children_descriptions?.value[i].value.name.value;
      res[name] = this.resourceData?.value.children?.value[i];
    }
    return res;
  };

}
