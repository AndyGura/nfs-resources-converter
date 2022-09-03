import { Component } from '@angular/core';
import { GuiComponentInterface } from '../../gui-component.interface';

@Component({
  selector: 'app-array.block-ui',
  templateUrl: './array.block-ui.component.html',
  styleUrls: ['./array.block-ui.component.scss']
})
export class ArrayBlockUiComponent implements GuiComponentInterface {

  private _resourceData: ReadData | null = null;
  get resourceData(): ReadData | null {
    return this._resourceData;
  }
  set resourceData(value: ReadData | null) {
    this._resourceData = value;
    this.showAsCollapsable = this._resourceData?.value?.length > 5
  }
  name: string = '';

  showAsCollapsable: boolean = false;
  renderContents: boolean = false;
  contentsTimeout: number | undefined;

  constructor() {
  }

  onContentsTrigger(open: boolean): void {
    if (this.contentsTimeout !== undefined) {
      clearTimeout(this.contentsTimeout);
      this.contentsTimeout = undefined;
    }
    if (open) {
      this.renderContents = true;
    } else {
      this.contentsTimeout = setTimeout(() => {
        this.contentsTimeout = undefined;
        this.renderContents = false;
      }, 2000);
    }
  }

}
