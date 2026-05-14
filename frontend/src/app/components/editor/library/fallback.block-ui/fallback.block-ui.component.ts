import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { GuiComponentInterfaceNew } from '../../gui-component.interface';
import { BlockSchema } from '../../types';

@Component({
  selector: 'app-fallback-block-ui',
  templateUrl: './fallback.block-ui.component.html',
  styleUrls: ['./fallback.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FallbackBlockUiComponent implements GuiComponentInterfaceNew {
  @Input() resourceId: string = '';
  @Input() resourceName: string = '';
  @Input() resourceSchema: BlockSchema | null = null;
  @Input() resourceData: any = null;
  @Input() resourceDescription: string | undefined = undefined;

  hideName?: boolean | undefined;
  hideBlockActions?: boolean | undefined;
  disabled?: boolean | undefined;
  @Output('changed') changed: EventEmitter<void> = new EventEmitter<void>();

  get displayClass(): string {
    if (this.resourceSchema) {
      return this.resourceSchema.block_class_mro.replace(/__/g, ' &rarr; ');
    }
    return 'Unknown';
  }

  constructor() {}
}
