import { ChangeDetectionStrategy, Component, Input, ViewChild } from '@angular/core';
import { SubscribableGuiComponent } from '../../gui.component';
import { joinId } from '../../../../utils/join-id';
import { NavigationService } from '../../../../services/navigation.service';
import { BlockData, BlockSchema, Resource } from '../../types';

import { ArrayTableColumn, DataTableComponent } from '../../common/data-table/data-table.component';
import { blockClassStr } from '../../../../utils/block_class_str';

@Component({
  selector: 'app-array-block-ui',
  templateUrl: './array.block-ui.component.html',
  styleUrls: ['./array.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  standalone: false,
})
export class ArrayBlockUiComponent extends SubscribableGuiComponent {
  override get resourceSchema(): BlockSchema {
    return super.resourceSchema;
  }

  @Input()
  override set resourceSchema(value: BlockSchema) {
    super.resourceSchema = value;
    this.checkIfTable();
    if (this.isTable) {
      this.renderContents = true;
    }
    this.buildChildren();
    this.renderPage(0, this.minPageSize);
    this.updatePageIndexes();
    this.updatePagedData();
  }

  override get resourceData(): BlockData[] | undefined {
    return super.resourceData;
  }

  @Input()
  override set resourceData(value: BlockData[] | undefined) {
    super.resourceData = value;
    this.checkIfTable();
    if (this.isTable) {
      this.renderContents = true;
    }
    this.buildChildren();
    this.renderPage(0, this.minPageSize);
    this.updatePageIndexes();
    this.updatePagedData();
  }

  protected buildChildren(): void {
    this.children = (super.resourceData || []).map((d: BlockData, i: number) => ({
      id: joinId(this.resourceId!, i),
      name: '' + i,
      data: d,
      schema: this.resourceSchema!.child_schema,
    }));
  }

  onFocusedElement(event: [string[], number]) {
    const [path, index] = event;
    this.onFocus(index.toString(), ...path);
  }

  renderContents: boolean = false;
  contentsTimeout: number | undefined;

  minPageSize: number = 10;
  pageIndex: number = 0;
  pageSize: number = 0;
  pageSizeOptions = [10, 25, 50, 100];
  protected children: Resource[] = [];
  goToIndex: number = 0;
  pageIndexes: number[] = [];
  public pagedData: any[] = [];

  protected readonly joinId = joinId;
  public readonly tableMaxHeight = 'calc((100vh - 64px) * 0.9)';
  @ViewChild(DataTableComponent) dataTable?: DataTableComponent;

  get enableArrayEditing(): boolean {
    return (
      !this.resourceSchema?.block_class_mro?.includes('SubByteArrayBlock') &&
      !this.resourceSchema?.length &&
      this.resourceSchema?.length !== 0
    );
  }

  override onExternalChanges() {
    this.buildChildren();
    this.updatePageIndexes();
    if (this.pageIndex >= this.pageIndexes.length && this.pageIndex > 0) {
      this.pageIndex--;
    }
    this.renderPage(this.pageIndex, this.pageSize);
    this.updatePagedData();
    this.dataTable?.markForCheck();
    super.onExternalChanges();
  }

  constructor(public readonly navigation: NavigationService) {
    super();
  }

  async addItem() {
    if (!this.resourceId || this.resourceData === undefined || !this.enableArrayEditing) return;
    const newItem = await this.mainService.getNewItemData(this.resourceId);
    if (newItem === null) return;
    this.emitNewChange({
      op: 'array_insert',
      index: this.resourceData.length,
      value: newItem,
    });
  }

  removeItem(index: number) {
    if (!this.resourceId || this.resourceData === undefined || !this.enableArrayEditing) return;
    this.emitNewChange({
      op: 'array_remove',
      index: index,
      oldValue: this.resourceData[index],
    });
  }

  moveItemUp(index: number) {
    if (index <= 0 || !this.resourceId || this.resourceData === undefined) return;
    this.emitNewChange({
      op: 'array_swap',
      indexA: index,
      indexB: index - 1,
    });
  }

  moveItemDown(index: number) {
    if (this.resourceData === undefined || !this.resourceId || index >= this.resourceData.length - 1) return;
    this.emitNewChange({
      op: 'array_swap',
      indexA: index,
      indexB: index + 1,
    });
  }

  get isTable(): boolean {
    return !!this.tableColumns && this.tableColumns.length > 0;
  }

  tableBlockTypeWhitelist = [
    'IntegerBlock',
    'FixedPointBlock',
    'DecimalBlock',
    'UTF8Block',
    'NullTerminatedUTF8Block',
    'EnumByteBlock',
  ];
  tableColumns: string[] | null = null;
  arrayTableColumns: ArrayTableColumn[] | null = null;

  private checkIfTable(): void {
    const childSchema = this.resourceSchema?.child_schema;
    if (!childSchema) {
      return;
    }
    const mro = childSchema.block_class_mro || '';
    const isWhitelisted = (className: string) => {
      return this.tableBlockTypeWhitelist.some(w => className.startsWith(w + '__'));
    };

    if (isWhitelisted(mro)) {
      this.tableColumns = ['index', 'data'];
      this.arrayTableColumns = [
        {
          key: 'data',
          index: 0,
          schema: childSchema,
          readonly: childSchema.value_validator?.type === 'eq',
        },
      ];
    } else if (mro.includes('CompoundBlock__')) {
      const fields = childSchema.fields || [];
      const uiFields = fields
        .map((f: any, i: number) => ({ ...f, index: i }))
        .filter((f: any) => !f.usage || f.usage === 'everywhere' || f.usage.includes('ui'));

      const isNestedWhitelisted = (f: any) => {
        const nestedMro = f.schema.block_class_mro || '';
        if (isWhitelisted(nestedMro)) {
          return true;
        }
        if (nestedMro.includes('CompoundBlock__')) {
          const subFields = (f.schema.fields || []).filter(
            (sf: any) => !sf.usage || sf.usage === 'everywhere' || sf.usage.includes('ui'),
          );
          return subFields.length > 0 && subFields.every((sf: any) => isWhitelisted(sf.schema.block_class_mro || ''));
        }
        return false;
      };

      const allChildrenWhitelisted = uiFields.every(isNestedWhitelisted);
      if (allChildrenWhitelisted && uiFields.length > 0) {
        this.arrayTableColumns = uiFields.map((f: any) => {
          const nestedMro = f.schema.block_class_mro || '';
          if (nestedMro.includes('CompoundBlock__')) {
            const subFields = (f.schema.fields || [])
              .map((sf: any, i: number) => ({ ...sf, index: i }))
              .filter((sf: any) => !sf.usage || sf.usage === 'everywhere' || sf.usage.includes('ui'));
            return {
              key: f.name,
              index: f.index,
              description: f.description,
              subFields: subFields.map((sf: any) => ({
                key: sf.name,
                index: sf.index,
                readonly: sf.schema.value_validator?.type === 'eq',
                description: sf.description,
                schema: sf.schema,
              })),
              readonly: false, // compound itself isn't editable as a single value
              schema: f.schema,
            };
          }
          return {
            key: f.name,
            index: f.index,
            readonly: f.schema.value_validator?.type === 'eq',
            description: f.description,
            schema: f.schema,
          };
        });
        this.tableColumns = ['index', ...this.arrayTableColumns!.map(f => f.key)];
      }
    }
  }

  onTableDataChanged(event: { index: number; field: string | null; subField: string | null; value: any }): void {
    if (!this.resourceId || this.resourceData === undefined) return;
    const { index, field, subField, value } = event;
    if (field) {
      if (subField) {
        this.onValueSet(value, index, field, subField);
      } else if (typeof this.resourceData[index] === 'object' && this.resourceData[index] !== null) {
        this.onValueSet(value, index, field);
      } else {
        this.onValueSet(value, index);
      }
    } else {
      this.onValueSet(value, index);
    }
    this.updatePagedData();
    this.cdr.markForCheck();
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
      }, 2000) as any as number;
    }
  }

  itemLabel(index: number) {
    let label = index.toString();
    if (this.resourceSchema && this.resourceSchema.block_class_mro.includes('DelegateBlock__')) {
      label += ` (${blockClassStr(this.resourceSchema.possible_resource_schemas[this.resourceData![index].choice_index])})`;
    }
    return label;
  }

  onPageIndexChange(event: number) {
    this.pageIndex = event;
    this.updatePageIndexes();
    this.updatePagedData();
    this.cdr.markForCheck();
  }

  onPageSizeChange(event: number) {
    this.pageSize = event;
    this.updatePageIndexes();
    this.updatePagedData();
    this.cdr.markForCheck();
  }

  renderPage(pageIndex: number, pageSize: number) {
    this.pageIndex = pageIndex;
    this.pageSize = pageSize;
    this.goToIndex = pageIndex;

    this.updatePagedData();
    this.cdr.markForCheck();
  }

  updatePageIndexes() {
    this.goToIndex = this.pageIndex;
    this.pageIndexes = [];
    if (this.pageSize > 0) {
      for (let i = 0; i < Math.ceil((super.resourceData || []).length / this.pageSize); i++) {
        this.pageIndexes.push(i);
      }
    }
  }

  private updatePagedData(): void {
    if (this.pageSize > 0) {
      this.pagedData = (super.resourceData || []).slice(
        this.pageIndex * this.pageSize,
        (this.pageIndex + 1) * this.pageSize,
      );
    } else {
      this.pagedData = super.resourceData || [];
    }
  }

  trackByFn(index: number, item: any): any {
    return index;
  }
}
