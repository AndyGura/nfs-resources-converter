import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { GuiComponentInterface } from '../../gui-component.interface';
import { BlockSchema } from '../../types';
import { MainService } from '../../../../services/main.service';
import { isNaN } from 'lodash';

@Component({
  selector: 'app-string-block-ui',
  templateUrl: './string.block-ui.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class StringBlockUiComponent implements GuiComponentInterface {
  @Input() resourceId?: string;
  @Input() resourceName?: string;

  private _resourceSchema?: BlockSchema;
  get resourceSchema(): BlockSchema {
    return this._resourceSchema;
  }

  @Input()
  set resourceSchema(value: BlockSchema) {
    this._resourceSchema = value;
    if (!isNaN(+this._resourceSchema?.length)) {
      this.minLength = this.maxLength = +this._resourceSchema?.length;
    }
  }

  @Input() resourceData?: string;
  @Input() resourceDescription?: string;

  @Input() hideName?: boolean;
  @Input() hideBlockActions?: boolean;
  @Input() disabled?: boolean;

  @Output('changed') changed: EventEmitter<string> = new EventEmitter<string>();

  minLength: number | null = null;
  maxLength: number | null = null;

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
