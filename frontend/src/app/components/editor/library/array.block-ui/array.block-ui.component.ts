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
    this.tableColumns = null;
    this.arrayTableColumns = null;
    const childSchema = this.resourceSchema?.child_schema;
    if (!childSchema) {
      return;
    }

    const isWhitelisted = (className: string) => {
      return this.tableBlockTypeWhitelist.some(w => className.startsWith(w + '__'));
    };

    const getArrayLength = (arrSchema: BlockSchema, arrays?: any[]): number | undefined => {
      if (typeof arrSchema.length === 'number') {
        return arrSchema.length;
      }
      return undefined;
    };

    const getCompoundSubFields = (compSchema: BlockSchema): any[] | null => {
      const fields = compSchema.fields || [];
      const uiFields = fields
        .map((f: any, i: number) => ({ ...f, index: i }))
        .filter((f: any) => !f.usage || f.usage === 'everywhere' || f.usage.includes('ui'));
      if (uiFields.length === 0) return null;

      const subFields: any[] = [];
      for (const f of uiFields) {
        const nestedMro = f.schema.block_class_mro || '';
        if (isWhitelisted(nestedMro)) {
          subFields.push({
            key: f.name,
            index: f.index,
            readonly: f.schema.value_validator?.type === 'eq',
            description: f.description,
            schema: f.schema,
          });
        } else {
          return null; // Nested compounds or arrays are not allowed inside subfields (limit to 2 levels)
        }
      }
      return subFields;
    };

    const mro = childSchema.block_class_mro || '';

    // Case 1: Rows are primitives
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
      return;
    }

    // Case 2: Rows are ArrayBlocks (2D arrays or arrays of compounds)
    if (mro.includes('ArrayBlock__')) {
      const innerChildSchema = childSchema.child_schema;
      if (!innerChildSchema) return;
      const innerMro = innerChildSchema.block_class_mro || '';

      const innerLength = getArrayLength(childSchema, this.resourceData);
      if (innerLength !== undefined && innerLength > 0 && innerLength <= 32) {
        // Elements of the array can be primitive
        if (isWhitelisted(innerMro)) {
          this.arrayTableColumns = [];
          for (let idx = 0; idx < innerLength; idx++) {
            this.arrayTableColumns.push({
              key: idx.toString(),
              index: idx,
              schema: innerChildSchema,
              readonly: innerChildSchema.value_validator?.type === 'eq',
            });
          }
          this.tableColumns = ['index', ...this.arrayTableColumns.map(f => f.key)];
          return;
        }
        // Elements of the array can be compound
        if (innerMro.includes('CompoundBlock__')) {
          const subFields = getCompoundSubFields(innerChildSchema);
          if (subFields) {
            this.arrayTableColumns = [];
            for (let idx = 0; idx < innerLength; idx++) {
              this.arrayTableColumns.push({
                key: idx.toString(),
                index: idx,
                schema: innerChildSchema,
                subFields: subFields.map(sf => ({ ...sf })), // deep-ish clone to avoid sharing same subfields across columns
                readonly: false,
              });
            }
            this.tableColumns = ['index', ...this.arrayTableColumns.map(f => f.key)];
            return;
          }
        }
      }
      return;
    }

    // Case 3: Rows are CompoundBlocks (compounds of primitives, compounds of compounds, or compounds of arrays)
    if (mro.includes('CompoundBlock__')) {
      const fields = childSchema.fields || [];
      const uiFields = fields
        .map((f: any, i: number) => ({ ...f, index: i }))
        .filter((f: any) => !f.usage || f.usage === 'everywhere' || f.usage.includes('ui'));
      if (uiFields.length === 0) return;

      const columns: ArrayTableColumn[] = [];

      for (const f of uiFields) {
        const nestedMro = f.schema.block_class_mro || '';

        // Subcase 3a: Field is primitive
        if (isWhitelisted(nestedMro)) {
          columns.push({
            key: f.name,
            index: f.index,
            readonly: f.schema.value_validator?.type === 'eq',
            description: f.description,
            schema: f.schema,
          });
        }
        // Subcase 3b: Field is compound of primitives
        else if (nestedMro.includes('CompoundBlock__')) {
          const subFields = getCompoundSubFields(f.schema);
          if (subFields) {
            columns.push({
              key: f.name,
              index: f.index,
              description: f.description,
              subFields: subFields,
              readonly: false,
              schema: f.schema,
            });
          } else {
            return; // Not simple if compound nested field cannot be simplified
          }
        }
        // Subcase 3c: Field is array of primitives (e.g. array_comp_array)
        else if (nestedMro.includes('ArrayBlock__')) {
          const innerChildSchema = f.schema.child_schema;
          if (!innerChildSchema) return;
          const innerMro = innerChildSchema.block_class_mro || '';

          if (isWhitelisted(innerMro)) {
            const fieldArrays = this.resourceData
              ? this.resourceData.map(row => (row ? row[f.name] : undefined))
              : undefined;
            const innerLength = getArrayLength(f.schema, fieldArrays);
            if (innerLength !== undefined && innerLength > 0 && innerLength <= 32) {
              const subFields: any[] = [];
              for (let idx = 0; idx < innerLength; idx++) {
                subFields.push({
                  key: idx.toString(),
                  index: idx,
                  readonly: innerChildSchema.value_validator?.type === 'eq',
                  schema: innerChildSchema,
                });
              }
              columns.push({
                key: f.name,
                index: f.index,
                description: f.description,
                subFields: subFields,
                readonly: false,
                schema: f.schema,
              });
            } else {
              return; // Invalid or too long array
            }
          } else {
            return; // Non-primitive elements inside array field
          }
        } else {
          return; // Unknown or complex field type
        }
      }

      this.arrayTableColumns = columns;
      this.tableColumns = ['index', ...columns.map(f => f.key)];
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
