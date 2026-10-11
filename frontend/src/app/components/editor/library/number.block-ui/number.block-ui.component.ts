import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  DoCheck,
  EventEmitter,
  inject,
  Input,
  Output,
} from '@angular/core';
import { PrimitiveGuiComponent, GuiComponent } from '../../gui.component';
import { BlockSchema } from '../../types';
import { MainService } from '../../../../services/main.service';
import { ChangesService } from '../../../../services/changes.service';
import { clampToRange, NumberRange, numberRange } from '../../value-validators';

@Component({
  selector: 'app-number-block-ui',
  templateUrl: './number.block-ui.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  standalone: false,
})
export class NumberBlockUiComponent extends PrimitiveGuiComponent<number> {
  get range(): NumberRange {
    return numberRange(this.resourceSchema);
  }

  // a typed value outside the range of the field is set to the nearest bound
  onInputChange(input: HTMLInputElement) {
    const value = clampToRange(+input.value, this.range);
    input.value = String(value);
    this.onValueSet(value);
  }
}
