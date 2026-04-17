import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  EventEmitter,
  Input,
  Output,
} from '@angular/core';
import { isNaN } from 'lodash';

export interface ArrayTableColumn {
  key: string;
  index: number;
  readonly?: boolean;
  description?: string;
  subFields?: { key: string; index: number; readonly?: boolean; description?: string }[];
  schema?: any;
}

@Component({
  selector: 'data-table',
  templateUrl: './data-table.component.html',
  styleUrls: ['./data-table.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DataTableComponent {

  private _columns: ArrayTableColumn[] | null = null;
  get columns(): ArrayTableColumn[] | null {
    return this._columns;
  }
  @Input()
  set columns(value: ArrayTableColumn[] | null) {
    this._columns = value;
    this.hasSubFields = value?.some(col => col.subFields && col.subFields.length > 0) || false;
  }

  @Input() data: any[] = [];
  @Input() itemSchema: any = null;
  @Input() renderIndexes: number[] = [];
  @Input() disabled: boolean = false;
  @Input() enableArrayEditing: boolean = false;
  @Input() pageIndex: number = 0;
  @Input() pageSize: number = 0;

  @Output() addItem = new EventEmitter<void>();
  @Output() removeItem = new EventEmitter<number>();
  @Output() moveItemUp = new EventEmitter<number>();
  @Output() moveItemDown = new EventEmitter<number>();
  @Output() dataChanged = new EventEmitter<{ index: number; field: string | null; subField: string | null; value: any }>();
  @Output() focusedElement = new EventEmitter<[string[], number]>();

  public hasSubFields: boolean = false;

  constructor(
    private cdr: ChangeDetectorRef,
  ) {}

  isNumeric(mro: string): boolean {
    return ['IntegerBlock', 'FixedPointBlock', 'DecimalBlock'].some((w) => mro.startsWith(w + '__'));
  }

  isString(mro: string): boolean {
    return ['UTF8Block', 'NullTerminatedUTF8Block'].some((w) => mro.startsWith(w + '__'));
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
}
