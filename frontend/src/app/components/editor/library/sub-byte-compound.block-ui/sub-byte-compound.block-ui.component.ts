import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { GuiComponentInterface } from '../../gui-component.interface';
import { Resource } from '../../types';
import { MainService } from '../../../../services/main.service';
import { joinId } from '../../../../utils/join-id';

@Component({
  selector: 'app-sub-byte-compound-block-ui',
  templateUrl: './sub-byte-compound.block-ui.component.html',
  styleUrls: [],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SubByteCompoundBlockUiComponent implements GuiComponentInterface {
  @Input() resource: Resource | null = null;

  @Input()
  resourceDescription: string = '';

  @Input()
  disabled: boolean = false;

  @Output('changed') changed: EventEmitter<void> = new EventEmitter<void>();

  constructor(private mainService: MainService) {}

  onFocus(alias: string) {
    if (this.resource) {
      this.mainService.focusedResourceId$.next(joinId(this.resource.id, alias));
    }
  }

  onBlur(alias: string) {
    if (this.mainService.focusedResourceId$.getValue() === joinId(this.resource?.id || '', alias)) {
      this.mainService.focusedResourceId$.next(null);
    }
  }
}
