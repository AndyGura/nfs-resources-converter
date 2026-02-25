import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { GuiComponentInterface } from '../../gui-component.interface';
import { Resource } from '../../types';

@Component({
  selector: 'app-skip-block-ui',
  template: '',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SkipBlockUiComponent implements GuiComponentInterface {
  @Input() resource: Resource | null = null;
  name: string = '';

  @Input()
  resourceDescription: string = '';

  @Output('changed') changed: EventEmitter<void> = new EventEmitter<void>();

  constructor() {}
}
