import {ChangeDetectionStrategy, ChangeDetectorRef, Component, EventEmitter, Input, Output} from '@angular/core';
import { GuiComponentInterface } from '../../gui-component.interface';
import {EelDelegateService} from "../../../../services/eel-delegate.service";
import {MainService} from "../../../../services/main.service";

@Component({
  selector: 'app-shpi-block-ui',
  templateUrl: './shpi.block-ui.component.html',
  styleUrls: ['./shpi.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ShpiBlockUiComponent implements GuiComponentInterface {

  @Input() resourceData: ReadData | null = null;
  name: string = '';
  isInEditState: boolean = false;

  @Output('changed') changed: EventEmitter<void> = new EventEmitter<void>();

  get resourcesMap(): { [key: string]: ReadData | ReadError } {
    const res: { [key: string]: ReadData | ReadError } = {};
    for (let i = 0; i < this.resourceData?.value.children_descriptions?.value.length; i++) {
      const name = this.resourceData?.value.children_descriptions?.value[i].value.name.value;
      res[name] = this.resourceData?.value.children?.value[i];
    }
    return res;
  };

  constructor(
    private readonly main: MainService,
    private readonly eel: EelDelegateService,
    private readonly cdr: ChangeDetectorRef,
  ) {
  }

  async onEditSHPIClicked() {
    if (this.resourceData) {
      const files = await this.eel.serializeResourceTmp(this.resourceData.block_id, []);
      const commonPathPart = files.reduce((commonBeginning, currentString) => {
        let j = 0;
        while (j < commonBeginning.length && j < currentString.length && commonBeginning[j] === currentString[j]) {
          j++;
        }
        return commonBeginning.substring(0, j);
      });
      await this.eel.openFileWithSystemApp(commonPathPart);
      this.isInEditState = true;
      this.cdr.markForCheck();
    }
  };

  async onUploadSHPIClicked() {
    if (this.resourceData) {
      await this.main.deserializeResource(this.resourceData.block_id);
      this.isInEditState = false;
      this.cdr.markForCheck();
    }
  };

}
