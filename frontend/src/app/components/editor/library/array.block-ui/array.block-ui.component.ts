import { ChangeDetectionStrategy, ChangeDetectorRef, Component, EventEmitter, Input, Output } from '@angular/core';
import { GuiComponentInterface } from '../../gui-component.interface';
import { joinId } from '../../../../utils/join-id';

@Component({
  selector: 'app-array-block-ui',
  templateUrl: './array.block-ui.component.html',
  styleUrls: ['./array.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ArrayBlockUiComponent implements GuiComponentInterface {
  private _resource: Resource | null = null;

  @Input()
  set resource(value: Resource | null) {
    this._resource = value;
    this.showAsCollapsable = this._resource?.data?.length > 5;
    this.buildChildren();
    this.renderPage(0, this.minPageSize);
    this.updatePageIndexes();
  }

  get resource(): Resource | null {
    return this._resource;
  }

  @Input()
  resourceDescription: string = '';

  get resourceData(): BlockData | null {
    return this._resource?.data;
  }

  protected buildChildren(): void {
    this.children = (this.resourceData || []).map((d: BlockData, i: number) => ({
      id: joinId(this._resource!.id, i),
      name: '' + i,
      data: d,
      schema: this._resource!.schema.child_schema,
    }));
  }

  @Output('changed') changed: EventEmitter<void> = new EventEmitter<void>();

  get schema(): BlockSchema | null {
    return this._resource?.schema;
  }

  get name(): string | null {
    return this._resource?.name || null;
  }

  showAsCollapsable: boolean = false;
  renderContents: boolean = false;
  contentsTimeout: number | undefined;

  minPageSize: number = 10;
  pageIndex: number = 0;
  pageSize: number = 0;
  pageSizeOptions = [10, 25, 50, 100];
  protected children: Resource[] = [];

  renderIndexes: number[] = [];
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
    if (this.pageSize !== pageSize) {
      this.renderIndexes = new Array(pageSize).fill(null).map((_, i) => i);
    }
    this.goToIndex = this.pageIndex = pageIndex;
    this.pageSize = pageSize;

    this.cdr.markForCheck();
  }

  updatePageIndexes() {
    this.goToIndex = this.pageIndex;
    this.pageIndexes = [];
    for (let i = 0; i < Math.ceil((this.resourceData || []).length / this.pageSize); i++) {
      this.pageIndexes.push(i);
    }
  }
}
