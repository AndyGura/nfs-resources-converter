import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { GuiComponentInterface } from '../../gui-component.interface';
import { MatSelectionListChange } from '@angular/material/list';

@Component({
  selector: 'app-flags-block-ui',
  templateUrl: './flags.block-ui.component.html',
  styleUrls: ['./flags.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FlagsBlockUiComponent implements GuiComponentInterface {
  @Input() resource: Resource | null = null;

  @Input()
  resourceDescription: string = '';

  @Input()
  disabled: boolean = false;

  @Output('changed') changed: EventEmitter<void> = new EventEmitter<void>();

  constructor() {}

  onSelection(event: MatSelectionListChange) {
    for (const option of event.options) {
      this.resource!.data[option.value] = option.selected;
    }
    this.changed.emit();
  }
}
