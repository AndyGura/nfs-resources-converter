import { ChangeDetectionStrategy, ChangeDetectorRef, Component, EventEmitter, Input, Output } from '@angular/core';
import { GuiComponentInterface } from '../../gui-component.interface';

@Component({
  selector: 'app-array-block-ui',
  templateUrl: './array.block-ui.component.html',
  styleUrls: ['./array.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ArrayBlockUiComponent implements GuiComponentInterface {
  private _resourceData: ReadData | null = null;
  get resourceData(): ReadData | null {
    return this._resourceData;
  }

  @Input()
  set resourceData(value: ReadData | null) {
    this._resourceData = value;
    this.showAsCollapsable = this._resourceData?.value?.length > 5;
    this.updatePageIndexes();
    this.renderPage(0, this.minPageSize);
  }

  name: string = '';

  @Output('changed') changed: EventEmitter<void> = new EventEmitter<void>();

  showAsCollapsable: boolean = false;
  renderContents: boolean = false;
  contentsTimeout: number | undefined;

  minPageSize: number = 10;
  pageIndex: number = 0;
  pageSize: number = 10;
  pageSizeOptions = [10, 25, 50, 100];
  renderItems: any[] = [];

  goToIndex: number = 0;
  pageIndexes: number[] = [];

  constructor(private readonly cdr: ChangeDetectorRef) {}

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
    this.goToIndex = this.pageIndex = pageIndex;
    this.pageSize = pageSize;
    this.renderItems = (this.resourceData?.value || [])
      .slice(pageIndex * pageSize, (pageIndex + 1) * pageSize)
      .map((x: ReadData) => (!!x['block'] ? x : { ...x, block: this.resourceData?.block.child }));
    this.cdr.markForCheck();
  }

  updatePageIndexes() {
    this.goToIndex = this.pageIndex;
    this.pageIndexes = [];
    for (let i = 0; i < Math.ceil((this.resourceData?.value || []).length / this.pageSize); i++) {
      this.pageIndexes.push(i);
    }
  }
}
