import { ChangeDetectionStrategy, ChangeDetectorRef, Component } from '@angular/core';
import { GuiComponentInterface } from '../../gui-component.interface';

@Component({
  selector: 'app-array.block-ui',
  templateUrl: './array.block-ui.component.html',
  styleUrls: ['./array.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ArrayBlockUiComponent implements GuiComponentInterface {

  private _resourceData: ReadData | null = null;
  get resourceData(): ReadData | null {
    return this._resourceData;
  }
  set resourceData(value: ReadData | null) {
    this._resourceData = value;
    this.showAsCollapsable = this._resourceData?.value?.length > 5;
    this.renderPage(0, this.minPageSize);
  }
  name: string = '';

  showAsCollapsable: boolean = false;
  renderContents: boolean = false;
  contentsTimeout: number | undefined;

  minPageSize: number = 10;
  pageIndex: number = 0;
  pageSize: number = 10;
  pageSizeOptions = [10, 25, 50, 100];
  renderItems: any[] = [];

  constructor(private readonly cdr: ChangeDetectorRef) {
  }

  onContentsTrigger(open: boolean): void {
    if (this.contentsTimeout !== undefined) {
      clearTimeout(this.contentsTimeout);
      this.contentsTimeout = undefined;
    }
    if (open) {
      this.renderContents = true;
      this.cdr.markForCheck();
    } else {
      this.contentsTimeout = setTimeout(() => {
        this.contentsTimeout = undefined;
        this.renderContents = false;
        this.cdr.markForCheck();
      }, 2000);
    }
  }

  renderPage(pageIndex: number, pageSize: number) {
    this.pageIndex = pageIndex;
    this.pageSize = pageSize;
    this.renderItems = (this.resourceData?.value || []).slice(pageIndex * pageSize, (pageIndex + 1) * pageSize);
    this.cdr.markForCheck();
  }

}
