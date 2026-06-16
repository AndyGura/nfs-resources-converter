import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  EventEmitter,
  Input,
  IterableDiffers,
  DoCheck,
  Output,
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
    this._pageIndex = value;
    this.updatePagedData();
  }
  get pageIndex(): number {
    return this._pageIndex;
  }

  private _pageSize: number = 0;
  @Input()
  set pageSize(value: number) {
    this._pageSize = value;
    this.updatePagedData();
  }
  get pageSize(): number {
    return this._pageSize;
  }

  @Input()
  set data(value: any[]) {
    this._data = value;
    this.isPrimitive = value && value.length > 0 && (typeof value[0] !== 'object' || value[0] === null);
    this.iterableDiffer = this.differs.find(value).create();
    this.updatePagedData();
  }
  get data(): any[] {
    return this._data;
  }
  private _data: any[] = [];
  @Input() disabled?: boolean = false;
  @Input() enableArrayEditing: boolean = false;

  public pagedData: any[] = [];
  private iterableDiffer: any;

  @Output() addItem = new EventEmitter<void>();
  @Output() removeItem = new EventEmitter<number>();
  @Output() moveItemUp = new EventEmitter<number>();
  @Output() moveItemDown = new EventEmitter<number>();
  @Output() dataChanged = new EventEmitter<{
    index: number;
    field: string | null;
    subField: string | null;
    value: any;
  }>();
  @Output() focusedElement = new EventEmitter<[string[], number]>();

  public hasSubFields: boolean = false;
  public isPrimitive: boolean = false;

  constructor(private cdr: ChangeDetectorRef, private differs: IterableDiffers) {}

  ngDoCheck(): void {
    const changes = this.iterableDiffer?.diff(this.data);
    if (changes) {
      this.updatePagedData();
      this.cdr.markForCheck();
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
    this.focusedElement.emit([columnIds, this.getGlobalIndex(index)]);
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
