import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { PrimitiveGuiComponent } from '../../gui.component';
import { BlockSchema } from '../../types';

@Component({
  selector: 'app-string-block-ui',
  templateUrl: './string.block-ui.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  standalone: false,
})
export class StringBlockUiComponent extends PrimitiveGuiComponent<string> {
  override get resourceSchema(): BlockSchema | undefined {
    return super.resourceSchema;
  }

  @Input()
  override set resourceSchema(value: BlockSchema | undefined) {
    super.resourceSchema = value;
    if (!isNaN(+this.resourceSchema?.length)) {
      this.minLength = this.maxLength = +this.resourceSchema?.length;
    }
  }

  @Output('changed') changed: EventEmitter<string> = new EventEmitter<string>();

  minLength: number | null = null;
  maxLength: number | null = null;
}
