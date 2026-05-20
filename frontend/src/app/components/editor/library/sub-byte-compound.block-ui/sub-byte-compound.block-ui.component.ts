import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { GuiComponentInterface } from '../../gui-component.interface';
import { BlockData, BlockSchema } from '../../types';
import { MainService } from '../../../../services/main.service';
import { joinId } from '../../../../utils/join-id';

@Component({
  selector: 'app-sub-byte-compound-block-ui',
  templateUrl: './sub-byte-compound.block-ui.component.html',
  styleUrls: [],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SubByteCompoundBlockUiComponent implements GuiComponentInterface {
  @Input() resourceId?: string;
  @Input() resourceName?: string;
  @Input() resourceSchema?: BlockSchema;
  @Input() resourceData?: BlockData;
  @Input() resourceDescription?: string;

  @Input() hideName?: boolean;
  @Input() hideBlockActions?: boolean;
  @Input() disabled?: boolean;

  @Output('changed') changed: EventEmitter<void> = new EventEmitter<void>();

  constructor(private mainService: MainService) {}

  onFocus(alias: string) {
    if (this.resourceId) {
      this.mainService.focusedResourceId$.next(joinId(this.resourceId, alias));
    }
  }

  onBlur(alias: string) {
    if (this.resourceId && this.mainService.focusedResourceId$.getValue() === joinId(this.resourceId, alias)) {
      this.mainService.focusedResourceId$.next(null);
    }
  }
}
