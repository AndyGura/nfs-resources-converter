import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  DoCheck,
  EventEmitter,
  Input,
  IterableDiffers,
  Output,
  ViewChild,
  ViewChildren,
  QueryList,
  ElementRef,
} from '@angular/core';

export interface ArrayTableColumn {
  key: string;
  index: number;
  readonly?: boolean;
  description?: string;
  subFields?: { key: string; index: number; readonly?: boolean; description?: string; schema?: any }[];
  schema?: any;
}

@Component({
  selector: 'data-table',
  templateUrl: './data-table.component.html',
  styleUrls: ['./data-table.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  standalone: false,
})
export class DataTableComponent implements DoCheck {
  private _columns: ArrayTableColumn[] | null = null;
  get columns(): ArrayTableColumn[] | null {
    return this._columns;
  }

  @Input()
  set columns(value: ArrayTableColumn[] | null) {
    this._columns = value;
    this.hasSubFields = value?.some(col => col.subFields && col.subFields.length > 0) || false;
  }

  private _pageIndex: number = 0;
  @Input()
  set pageIndex(value: number) {
    if (this._pageIndex !== value) {
      this._pageIndex = value;
      this.updatePagedData();
      this.pageIndexChange.emit(value);
    }
  }

  get pageIndex(): number {
    return this._pageIndex;
  }

  private _pageSize: number = 0;
  @Input()
  set pageSize(value: number) {
    if (this._pageSize !== value) {
      this._pageSize = value;
      this.updatePagedData();
      this.pageSizeChange.emit(value);
    }
  }

  get pageSize(): number {
    return this._pageSize;
  }

  @Input()
  set data(value: any[]) {
    this._data = value;
    this.isPrimitive = value && value.length > 0 && (typeof value[0] !== 'object' || value[0] === null);
    this.updatePagedData();
    this.cdr.markForCheck();
  }

  get data(): any[] {
    return this._data;
  }

  private _data: any[] = [];
  private previousDataLength: number = 0;
  @Input() disabled?: boolean = false;
  @Input() enableArrayEditing: boolean = false;
  @Input() selectedIndex: number | null = null;
  @Input() maxHeight?: string | null = null;
  @Input() usePaginator: boolean = false;
  @Input() pageSizeOptions: number[] = [10, 25, 50, 100];

  @ViewChild('tableContainer', { static: false }) tableContainer: any;
  @ViewChildren('focusableInput') focusableInputs!: QueryList<ElementRef>;

  public pagedData: any[] = [];
  private iterableDiffer: any;

  @Output() addItem = new EventEmitter<void>();
  @Output() removeItem = new EventEmitter<number>();
  @Output() moveItemUp = new EventEmitter<number>();
  @Output() moveItemDown = new EventEmitter<number>();
  @Output() pageIndexChange = new EventEmitter<number>();
  @Output() pageSizeChange = new EventEmitter<number>();
  @Output() dataChanged = new EventEmitter<{
    index: number;
    field: string | null;
    subField: string | null;
    value: any;
  }>();
  @Output() focusedElement = new EventEmitter<[string[], number]>();

  public hasSubFields: boolean = false;
  public isPrimitive: boolean = false;

  constructor(
    private cdr: ChangeDetectorRef,
    private differs: IterableDiffers,
  ) {}

  public markForCheck(): void {
    this.cdr.markForCheck();
  }

  ngDoCheck(): void {
    if (!this.iterableDiffer && this.data) {
      this.iterableDiffer = this.differs.find(this.data).create();
      this.iterableDiffer.diff(this.data);
      this.previousDataLength = this.data.length;
    }
    const changes = this.iterableDiffer?.diff(this.data);
    if (changes) {
      let isAdditionAtEnd = false;

      // We only care about additions if the total length increased
      if (this.data.length > this.previousDataLength) {
        changes.forEachAddedItem((record: any) => {
          // record.currentIndex is the new index.
          // record.previousIndex is null for new items.
          if (record.previousIndex === null && record.currentIndex === this.data.length - 1) {
            isAdditionAtEnd = true;
          }
        });
      }

      if (isAdditionAtEnd && this.usePaginator && this.pageSize > 0) {
        this.pageIndex = Math.floor((this.data.length - 1) / this.pageSize);
      }
      if (isAdditionAtEnd) {
        this.focusedElement.emit([[], this.data.length - 1]);
      }
      this.updatePagedData();
      this.cdr.markForCheck();

      if (isAdditionAtEnd) {
        setTimeout(() => {
          if (this.tableContainer) {
            this.tableContainer.nativeElement.scrollTop = this.tableContainer.nativeElement.scrollHeight;
          }
          // Focus the first non-readonly field of the new row
          const globalIdx = this.data.length - 1;
          const inputs = this.focusableInputs.toArray();
          // Each row has a set of inputs. We need to find the inputs belonging to the last row.
          // Since we might have pagination, the index in the pagedData is important.
          const localIdx = globalIdx - this.pageIndex * this.pageSize;
          const inputsPerRow = Math.floor(inputs.length / this.pagedData.length);
          const startIndex = localIdx * inputsPerRow;
          const lastRowInputs = inputs.slice(startIndex, startIndex + inputsPerRow);
          const firstEditable = lastRowInputs.find(input => !input.nativeElement.disabled);
          if (firstEditable) {
            firstEditable.nativeElement.focus();
          }
        }, 50); // Small delay to ensure ViewChildren is updated and DOM is ready
      }
      this.previousDataLength = this.data.length;
    }
  }

  isNumeric(mro: string): boolean {
    return ['IntegerBlock', 'FixedPointBlock', 'DecimalBlock'].some(w => mro.startsWith(w + '__'));
  }

  isString(mro: string): boolean {
    return ['UTF8Block', 'NullTerminatedUTF8Block'].some(w => mro.startsWith(w + '__'));
  }

  isEnum(mro: string): boolean {
    return mro.startsWith('EnumByteBlock__');
  }

  isKnownEnumValue(schema: any, value: any): boolean {
    return !!schema.enum_names.find(([_, v]: string[]) => v == value);
  }

  getMinLength(schema: any): number | null {
    if (!isNaN(+schema.length)) {
      return +schema.length;
    }
    return null;
  }

  getMaxLength(schema: any): number | null {
    if (!isNaN(+schema.length)) {
      return +schema.length;
    }
    return null;
  }

  onTableFieldChange(index: number, field: string | null, subField: string | null, value: any): void {
    this.dataChanged.emit({ index, field, subField, value });
    this.cdr.markForCheck();
  }

  onFocus(index: number, field: string | null, subField: string | null): void {
    const columnIds: string[] = [];
    if (field) columnIds.push(field);
    if (subField) columnIds.push(subField);
    this.focusedElement.emit([columnIds, index]);
  }

  onPageChange(event: any): void {
    this.pageSize = event.pageSize;
    this.pageIndex = event.pageIndex;
  }

  getGlobalIndex(i: number): number {
    return this.pageIndex * this.pageSize + i;
  }

  private updatePagedData(): void {
    if (this.pageSize > 0) {
      this.pagedData = this.data.slice(this.pageIndex * this.pageSize, (this.pageIndex + 1) * this.pageSize);
    } else {
      this.pagedData = this.data;
    }
  }

  trackByFn(index: number, item: any): any {
    return index;
  }
}
