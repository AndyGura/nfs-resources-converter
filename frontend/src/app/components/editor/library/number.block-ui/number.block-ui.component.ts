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

@Component({
  selector: 'app-number-block-ui',
  templateUrl: './number.block-ui.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  standalone: false,
})
export class NumberBlockUiComponent extends PrimitiveGuiComponent<number> {}
