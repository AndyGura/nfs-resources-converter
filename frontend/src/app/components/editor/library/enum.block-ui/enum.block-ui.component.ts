import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { GuiComponentInterface } from '../../gui-component.interface';
import { Resource } from '../../types';
import { MainService } from '../../../../services/main.service';

@Component({
  selector: 'app-enum-block-ui',
  templateUrl: './enum.block-ui.component.html',
  styleUrls: ['./enum.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EnumBlockUiComponent implements GuiComponentInterface {
  @Input() resource: Resource | null = null;

  @Input()
  resourceDescription: string = '';

  @Input()
  disabled: boolean = false;

  @Output('changed') changed: EventEmitter<void> = new EventEmitter<void>();

  isKnownEnumValue(value: string): boolean {
    return !!this.resource?.schema.enum_names.find(([_, v]: string[]) => v == value);
  }

  constructor(private mainService: MainService) {}

  onFocus() {
    if (this.resource) {
      this.mainService.focusedResourceId$.next(this.resource.id);
    }
  }

  onBlur() {
    if (this.mainService.focusedResourceId$.getValue() === this.resource?.id) {
      this.mainService.focusedResourceId$.next(null);
    }
  }
}
