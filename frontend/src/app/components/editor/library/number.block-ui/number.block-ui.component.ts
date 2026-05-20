import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { GuiComponentInterface } from '../../gui-component.interface';
import { BlockSchema } from '../../types';
import { MainService } from '../../../../services/main.service';

@Component({
  selector: 'app-number-block-ui',
  templateUrl: './number.block-ui.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class NumberBlockUiComponent implements GuiComponentInterface {
  @Input() resourceId?: string;
  @Input() resourceName?: string;
  @Input() resourceSchema?: BlockSchema;
  @Input() resourceData?: number;
  @Input() resourceDescription?: string;

  @Input() hideName?: boolean;
  @Input() hideBlockActions?: boolean;
  @Input() disabled?: boolean;

  @Output('changed') changed: EventEmitter<number> = new EventEmitter<number>();

  constructor(private mainService: MainService) {}

  onFocus() {
    if (this.resourceId) {
      this.mainService.focusedResourceId$.next(this.resourceId);
    }
  }

  onBlur() {
    if (this.mainService.focusedResourceId$.getValue() === this.resourceId) {
      this.mainService.focusedResourceId$.next(null);
    }
  }
}
