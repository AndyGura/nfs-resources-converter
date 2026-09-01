import { ChangeDetectionStrategy, Component } from '@angular/core';
import { SubscribableGuiComponent } from '../../gui.component';
import { BlockData } from '../../types';

// A TrailingOptionalBlock's data is the child's own value when present, or `null` when absent -
// there is no wrapper object to look inside, unlike e.g. DelegateBlock.
@Component({
  selector: 'app-trailing-optional-block-ui',
  templateUrl: './trailing-optional.block-ui.component.html',
  styleUrls: ['./trailing-optional.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  standalone: false,
})
export class TrailingOptionalBlockUiComponent extends SubscribableGuiComponent<BlockData | null> {
  get isPresent(): boolean {
    return this.resourceData !== null && this.resourceData !== undefined;
  }

  async setPresent(present: boolean): Promise<void> {
    if (!this.resourceId || present === this.isPresent) return;
    const oldValue = this.resourceData ?? null;
    const newValue = present ? await this.mainService.getTrailingOptionalFieldData(this.resourceId) : null;
    this.emitNewChange({ op: 'set', oldValue, newValue });
  }
}
