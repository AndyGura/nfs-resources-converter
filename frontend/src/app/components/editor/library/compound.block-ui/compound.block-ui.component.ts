import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { GuiComponentInterface } from '../../gui-component.interface';

@Component({
  selector: 'app-compound-block-ui',
  templateUrl: './compound.block-ui.component.html',
  styleUrls: ['./compound.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CompoundBlockUiComponent implements GuiComponentInterface {

  @Input() resourceData: ReadData | null = null;
  name: string = '';

  @Input() fieldWhitelist: string[] | null = null;

  @Input() fieldBlacklist: string[] | null = null;

  @Output('changed') changed: EventEmitter<void> = new EventEmitter<void>();

  get fieldKeys(): string[] {
    let fields = Object.keys(this.resourceData?.value || {});
    if (this.fieldWhitelist) {
      fields = fields.filter(x => this.fieldWhitelist?.includes(x));
    } else if (this.fieldBlacklist) {
      fields = fields.filter(x => !this.fieldBlacklist?.includes(x));
    }
    return fields;
  }

  constructor() {
  }

}
