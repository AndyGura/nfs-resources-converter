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
import { MainService } from '../../../../services/main.service';
import { BehaviorSubject, filter, Subject, takeUntil } from 'rxjs';
import { NavigationService } from '../../../../services/navigation.service';
import { idSuffix, joinId } from '../../../../utils/join-id';
import { BlockData, BlockSchema } from '../../types';

@Component({
  selector: 'app-compound-block-ui',
  templateUrl: './compound.block-ui.component.html',
  styleUrls: ['./compound.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CompoundBlockUiComponent implements GuiComponentInterface, AfterViewInit, OnDestroy {
  @Input() resourceId?: string;
  @Input() resourceName?: string;

  private _resourceSchema?: BlockSchema;
  get resourceSchema(): BlockSchema | undefined {
    return this._resourceSchema;
  }

  @Input()
  set resourceSchema(value: BlockSchema | undefined) {
    this._resourceSchema = value;
    this.updateFields();
  }

  @Input()
  resourceData?: BlockData;

  @Input() resourceDescription?: string;

  @Input() hideName?: boolean;
  @Input() hideBlockActions?: boolean;
  @Input() disabled?: boolean;

  @Input() preferHorizontalLayout: boolean = false;
  private _fieldWhitelist: string[] | null = null;
  get fieldWhitelist(): string[] | null {
    return this._fieldWhitelist;
  }

  @Input()
  set fieldWhitelist(value: string[] | null) {
    this._fieldWhitelist = value;
    this.updateFields();
  }

  private _fieldBlacklist: string[] | null = null;

  get fieldBlacklist(): string[] | null {
    return this._fieldBlacklist;
  }

  @Input()
  set fieldBlacklist(value: string[] | null) {
    this._fieldBlacklist = value;
    this.updateFields();
  }

  @Output('changed') changed: EventEmitter<void> = new EventEmitter<void>();

  fieldKeys$: BehaviorSubject<{ index: number; key: string }[]> = new BehaviorSubject<{ index: number; key: string }[]>(
    [],
  );

  updateFields() {
    if (this.resourceSchema) {
      let fields: { index: number; key: string }[] =
        this.resourceSchema.fields
          .map((f: { name: string; usage?: string }, i: number) => ({ index: i, name: f.name, usage: f.usage }))
          .filter((f: { usage?: string }) => !f.usage || f.usage == 'everywhere' || f.usage.includes('ui'))
          .map((f: { index: number; name: string }) => ({ index: f.index, key: f.name })) || [];
      if (this.fieldWhitelist) {
        fields = fields.filter(({ key }) => this.fieldWhitelist?.includes(key));
      } else if (this.fieldBlacklist) {
        fields = fields.filter(({ key }) => !this.fieldBlacklist?.includes(key));
      }
      this.fieldKeys$.next(fields);
    } else {
      this.fieldKeys$.next([]);
    }
  }

  fieldTrackBy(index: number, item: { index: number; key: string }) {
    return item.index;
  }

  private readonly destroyed$: Subject<void> = new Subject<void>();

  constructor(
    public readonly main: MainService,
    public readonly navigation: NavigationService,
    private readonly cdr: ChangeDetectorRef,
  ) {}

  ngAfterViewInit(): void {
    // TODO make this work in all components I guess?
    // FIXME do we actually need that with new model?
    this.main.dataBlockChange$
      .pipe(
        takeUntil(this.destroyed$),
        // handle inner primitive fields (1 level deep) and update object with new values.
        // this makes effect only locally in frontend
        filter(
          ([blockId]) =>
            !!this.resourceId &&
            !!this.resourceData &&
            blockId.startsWith(this.resourceId) &&
            !blockId.substring(this.resourceId.length + 1).includes('/'),
        ),
      )
      .subscribe(async ([blockId, value]) => {
        if (blockId === this.resourceId) {
          this.resourceData = value;
          return;
        }
        this.resourceData![idSuffix(this.resourceId!, blockId)] = value;
        this.cdr.markForCheck();
      });
  }

  ngOnDestroy(): void {
    this.destroyed$.next();
    this.destroyed$.complete();
  }

  protected readonly joinId = joinId;
}
