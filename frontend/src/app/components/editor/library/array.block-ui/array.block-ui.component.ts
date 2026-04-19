import {
  AfterViewInit,
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  EventEmitter,
  Input,
  OnDestroy,
  Output,
} from '@angular/core';
import { GuiComponentInterface } from '../../gui-component.interface';
import { idSuffix, joinId } from '../../../../utils/join-id';
import { MainService } from '../../../../services/main.service';
import { filter, Subject, takeUntil } from 'rxjs';
import { NavigationService } from '../../../../services/navigation.service';
import { BlockData, BlockSchema, Resource } from '../../types';

import { ArrayTableColumn } from '../../common/data-table/data-table.component';

@Component({
  selector: 'app-array-block-ui',
  templateUrl: './array.block-ui.component.html',
  styleUrls: ['./array.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ArrayBlockUiComponent implements GuiComponentInterface, AfterViewInit, OnDestroy {
  private _resource: Resource | null = null;

  @Input()
  set resource(value: Resource | null) {
    this._resource = value;
    this.checkIfTable();
    if (this.isTable) {
      this.renderContents = true;
    }
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

  @Input() disabled: boolean = false;

  @Output('changed') changed: EventEmitter<void> = new EventEmitter<void>();

  get schema(): BlockSchema | null {
    return this._resource?.schema;
  }

  get name(): string | null {
    return this._resource?.name || null;
  }

  renderContents: boolean = false;
  contentsTimeout: number | undefined;

  minPageSize: number = 10;
  pageIndex: number = 0;
  pageSize: number = 0;
  pageSizeOptions = [10, 25, 50, 100];
  protected children: Resource[] = [];

  renderIndexes: number[] = []; // TODO remove that
  goToIndex: number = 0;
  pageIndexes: number[] = [];

  private readonly destroyed$: Subject<void> = new Subject<void>();

  protected readonly joinId = joinId;

  get enableArrayEditing(): boolean {
    return (
      !this.schema?.block_class_mro?.includes('SubByteArrayBlock')
      && (!this.schema?.length && this.schema?.length !== 0)
    );
  }

  constructor(
    public main: MainService,
    private readonly cdr: ChangeDetectorRef,
    public readonly navigation: NavigationService,
  ) {
  }

  async addItem() {
    if (!this.resource || !this.enableArrayEditing) return;
    const newItem = await this.main.getNewItemData(this.resource.id);
    if (newItem === null) return;
    this.resourceData.push(newItem);
    this.buildChildren();
    this.updatePageIndexes();
    this.pageIndex = Math.max(0, this.pageIndexes.length - 1);
    this.renderPage(this.pageIndex, this.pageSize);
    this.main.dataBlockChange$.next([this.resource.id, this.resourceData]);
    this.cdr.markForCheck();
  }

  removeItem(index: number) {
    if (!this.resource || !this.enableArrayEditing) return;
    this.resourceData.splice(index, 1);
    this.buildChildren();
    this.updatePageIndexes();
    if (this.pageIndex >= this.pageIndexes.length && this.pageIndex > 0) {
      this.pageIndex--;
    }
    this.renderPage(this.pageIndex, this.pageSize);
    this.main.dataBlockChange$.next([this.resource.id, this.resourceData]);
    this.cdr.markForCheck();
  }

  moveItemUp(index: number) {
    if (index <= 0 || !this.resource) return;
    const temp = this.resourceData[index];
    this.resourceData[index] = this.resourceData[index - 1];
    this.resourceData[index - 1] = temp;
    this.buildChildren();
    this.renderPage(this.pageIndex, this.pageSize);
    this.main.dataBlockChange$.next([this.resource.id, this.resourceData]);
    this.cdr.markForCheck();
  }

  moveItemDown(index: number) {
    if (index >= this.resourceData.length - 1 || !this.resource) return;
    const temp = this.resourceData[index];
    this.resourceData[index] = this.resourceData[index + 1];
    this.resourceData[index + 1] = temp;
    this.buildChildren();
    this.renderPage(this.pageIndex, this.pageSize);
    this.main.dataBlockChange$.next([this.resource.id, this.resourceData]);
    this.cdr.markForCheck();
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
    'EnumByteBlock'
  ];
  tableColumns: string[] | null = null;
  arrayTableColumns: ArrayTableColumn[] | null = null;

  private checkIfTable(): void {
    const childSchema = this.schema?.child_schema;
    if (!childSchema) {
      return;
    }
    const mro = childSchema.block_class_mro || '';
    const isWhitelisted = (className: string) => {
      return this.tableBlockTypeWhitelist.some((w) => className.startsWith(w + '__'));
    };

    if (isWhitelisted(mro)) {
      this.tableColumns = ['index', 'data'];
      this.arrayTableColumns = [{
        key: 'data',
        index: 0,
        schema: childSchema,
        readonly: childSchema.value_validator?.type === 'eq',
      }];
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
          const subFields = (f.schema.fields || [])
            .filter((sf: any) => !sf.usage || sf.usage === 'everywhere' || sf.usage.includes('ui'));
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
        this.tableColumns = ['index', ...this.arrayTableColumns!.map((f) => f.key)];
      }
    }
  }

  ngAfterViewInit(): void {
    this.main.dataBlockChange$
      .pipe(
        takeUntil(this.destroyed$),
        // handle inner primitive fields (1 level deep) and update object with new values.
        // this makes effect only locally in frontend
        filter(
          ([blockId, value]) =>
            !!this.resource &&
            blockId.startsWith(this.resource!.id) &&
            !blockId.substring(this.resource!.id.length + 1).includes('/'),
        ),
      )
      .subscribe(async ([blockId, value]) => {
        if (blockId === this.resource!.id) {
          this.resource!.data = value;
          return;
        }
        this.resourceData[+idSuffix(this.resource!.id, blockId)] = value;
      });
  }

  ngOnDestroy(): void {
    this.destroyed$.next();
    this.destroyed$.complete();
  }

  onTableDataChanged(event: { index: number; field: string | null; subField: string | null; value: any }): void {
    if (!this.resource) return;
    const { index, field, subField, value } = event;
    const item = this.resourceData[index];
    let targetId = joinId(this.resource.id, index);

    if (field) {
      targetId = joinId(targetId, field);
      if (subField) {
        targetId = joinId(targetId, subField);
        item[field][subField] = value;
      } else if (typeof item === 'object' && item !== null) {
        item[field] = value;
      } else {
        this.resourceData[index] = value;
      }
    } else {
      this.resourceData[index] = value;
    }

    this.main.dataBlockChange$.next([targetId, value]);
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

  renderPage(pageIndex: number, pageSize: number) {
    this.pageIndex = pageIndex;
    this.pageSize = pageSize;
    this.goToIndex = pageIndex;
    const totalItems = (this.resourceData || []).length;
    const itemsOnPage = Math.min(pageSize, totalItems - pageIndex * pageSize);
    this.renderIndexes = Array.from(Array(Math.max(0, itemsOnPage)).keys());

    this.cdr.markForCheck();
  }

  updatePageIndexes() {
    this.goToIndex = this.pageIndex;
    this.pageIndexes = [];
    if (this.pageSize > 0) {
      for (let i = 0; i < Math.ceil((this.resourceData || []).length / this.pageSize); i++) {
        this.pageIndexes.push(i);
      }
    }
  }
}
