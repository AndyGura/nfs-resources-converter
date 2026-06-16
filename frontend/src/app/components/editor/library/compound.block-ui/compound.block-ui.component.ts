import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { SubscribableGuiComponent } from '../../gui.component';
import { MainService } from '../../../../services/main.service';
import { BehaviorSubject } from 'rxjs';
import { NavigationService } from '../../../../services/navigation.service';
import { joinId } from '../../../../utils/join-id';
import { BlockData, BlockSchema } from '../../types';

@Component({
  selector: 'app-compound-block-ui',
  templateUrl: './compound.block-ui.component.html',
  styleUrls: ['./compound.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  standalone: false,
})
export class CompoundBlockUiComponent extends SubscribableGuiComponent<{ [key: string]: BlockData }> {
  override get resourceSchema(): BlockSchema | undefined {
    return super.resourceSchema;
  }

  @Input()
  override set resourceSchema(value: BlockSchema | undefined) {
    super.resourceSchema = value;
    this.updateFields();
  }

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

  constructor(
    public readonly main: MainService,
    public readonly navigation: NavigationService,
  ) {
    super();
  }

  protected readonly joinId = joinId;
}
