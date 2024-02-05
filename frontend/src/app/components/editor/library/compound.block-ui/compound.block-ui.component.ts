import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { GuiComponentInterface } from '../../gui-component.interface';
import { MainService } from '../../../../services/main.service';

@Component({
  selector: 'app-compound-block-ui',
  templateUrl: './compound.block-ui.component.html',
  styleUrls: ['./compound.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CompoundBlockUiComponent implements GuiComponentInterface {
  @Input() resource: Resource | null = null;

  @Input() resourceDescription: string = '';

  @Input() hideBlockActions: boolean = false;

  get name(): string | null {
    return this.resource && this.resource.name;
  }
  get data(): BlockData | null {
    return this.resource && this.resource.data;
  }
  get schema(): BlockSchema | null {
    return this.resource && this.resource.schema;
  }

  @Input() fieldWhitelist: string[] | null = null;

  @Input() fieldBlacklist: string[] | null = null;

  @Output('changed') changed: EventEmitter<void> = new EventEmitter<void>();

  get fieldKeys(): { index: number; key: string }[] {
    let fields: { index: number; key: string }[] =
      this.schema?.fields.map((f: { name: string }, i: number) => ({ index: i, key: f.name })) || [];
    if (this.fieldWhitelist) {
      fields = fields.filter(({ key }) => this.fieldWhitelist?.includes(key));
    } else if (this.fieldBlacklist) {
      fields = fields.filter(({ key }) => !this.fieldBlacklist?.includes(key));
    }
    return fields;
  }

  fieldTrackBy(index: number, item: { index: number; key: string }) {
    return item.index;
  }

  constructor(public main: MainService) {}
}
