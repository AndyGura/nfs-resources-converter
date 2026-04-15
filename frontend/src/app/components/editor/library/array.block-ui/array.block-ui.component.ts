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

  renderIndexes: number[] = [];
  goToIndex: number = 0;
  pageIndexes: number[] = [];

  private readonly destroyed$: Subject<void> = new Subject<void>();

  protected readonly joinId = joinId;

  constructor(
    public main: MainService,
    private readonly cdr: ChangeDetectorRef,
    public readonly navigation: NavigationService,
  ) {
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
  tableCompoundFields: { key: string; index: number; subFields?: { key: string; index: number }[] }[] | null = null;
  hasSubFields: boolean = false;

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

  onTableFieldChange(parentId: string, index: number, field: string | null, value: any): void {
    // we do not want to emit "changed" here as we normally do, because it leads to change of whole array data
    // emit dataBlockChange$ directly instead
    if (field) {
      const data = this.resourceData[index];
      const parentParts = parentId.split('/');
      const lastPart = parentParts[parentParts.length - 1];

      if (isNaN(+lastPart)) {
        // nested compound
        data[lastPart][field] = value;
      } else {
        data[field] = value;
      }

      this.main.dataBlockChange$.next([joinId(parentId, field), value]);
    } else {
      this.resourceData[index] = value;
      this.main.dataBlockChange$.next([parentId, value]);
    }
  }

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
      this.hasSubFields = false;
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
        this.hasSubFields = uiFields.some((f: any) => (f.schema.block_class_mro || '').includes('CompoundBlock__'));
        this.tableCompoundFields = uiFields.map((f: any) => {
          const nestedMro = f.schema.block_class_mro || '';
          if (nestedMro.includes('CompoundBlock__')) {
            const subFields = (f.schema.fields || [])
              .map((sf: any, i: number) => ({ ...sf, index: i }))
              .filter((sf: any) => !sf.usage || sf.usage === 'everywhere' || sf.usage.includes('ui'));
            return {
              key: f.name,
              index: f.index,
              subFields: subFields.map((sf: any) => ({ key: sf.name, index: sf.index })),
            };
          }
          return { key: f.name, index: f.index };
        });
        this.tableColumns = ['index', ...this.tableCompoundFields!.map((f) => f.key)];
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
        this.resourceData[+idSuffix(this.resource!.id, blockId)] = value;
      });
  }

  ngOnDestroy(): void {
    this.destroyed$.next();
    this.destroyed$.complete();
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
