import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { GuiComponentInterface } from '../../gui-component.interface';
import { MatSelectionListChange } from '@angular/material/list';
import { Resource } from '../../types';

@Component({
  templateUrl: './fence-type.block-ui.component.html',
  styleUrls: [],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FenceTypeBlockUiComponent implements GuiComponentInterface {
  @Input() resource: Resource | null = null;

  @Input()
  resourceDescription: string = '';

  @Output('changed') changed: EventEmitter<void> = new EventEmitter<void>();

  onSelection(event: MatSelectionListChange) {
    for (const option of event.options) {
      this.resource!.data[option.value] = option.selected;
    }
    this.changed.emit();
  }
}
