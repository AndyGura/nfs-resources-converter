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
    'NullTerminatedUTF8Block'
  ];
  tableColumns: string[] | null = null;
  tableCompoundFields: { key: string; index: number }[] | null = null;

  isNumeric(mro: string): boolean {
    return ['IntegerBlock', 'FixedPointBlock', 'DecimalBlock'].some((w) => mro.startsWith(w + '__'));
  }

  isString(mro: string): boolean {
    return ['UTF8Block', 'NullTerminatedUTF8Block'].some((w) => mro.startsWith(w + '__'));
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
      this.resourceData[index][field] = value;
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
    } else if (mro.includes('CompoundBlock__')) {
      const fields = childSchema.fields || [];
      const uiFields = fields
        .map((f: any, i: number) => ({ ...f, index: i }))
        .filter((f: any) => !f.usage || f.usage === 'everywhere' || f.usage.includes('ui'));

      const allChildrenWhitelisted = uiFields.every((f: any) => isWhitelisted(f.schema.block_class_mro || ''));
      if (allChildrenWhitelisted && uiFields.length > 0) {
        this.tableCompoundFields = uiFields.map((f: any) => ({ key: f.name, index: f.index }));
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
