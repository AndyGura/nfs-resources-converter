import { ChangeDetectionStrategy, Component, EventEmitter, Output } from '@angular/core';
import { PrimitiveGuiComponent } from '../../gui.component';

@Component({
  selector: 'app-enum-block-ui',
  templateUrl: './enum.block-ui.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  standalone: false,
})
export class EnumBlockUiComponent extends PrimitiveGuiComponent<string | number> {
  isKnownEnumValue(value: string | number): boolean {
    return !!this.resourceSchema?.enum_names.find(([_, v]: string[]) => v == value);
  }
}
