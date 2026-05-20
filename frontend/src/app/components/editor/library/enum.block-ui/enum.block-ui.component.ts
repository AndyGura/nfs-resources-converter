import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { GuiComponentInterface } from '../../gui-component.interface';
import { BlockSchema } from '../../types';
import { MainService } from '../../../../services/main.service';

@Component({
  selector: 'app-enum-block-ui',
  templateUrl: './enum.block-ui.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EnumBlockUiComponent implements GuiComponentInterface {
  @Input() resourceId?: string;
  @Input() resourceName?: string;
  @Input() resourceSchema?: BlockSchema;
  @Input() resourceData?: string;
  @Input() resourceDescription?: string;

  @Input() hideName?: boolean;
  @Input() hideBlockActions?: boolean;
  @Input() disabled?: boolean;

  @Output('changed') changed: EventEmitter<string> = new EventEmitter<string>();

  isKnownEnumValue(value: string): boolean {
    return !!this.resourceSchema?.enum_names.find(([_, v]: string[]) => v == value);
  }

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
