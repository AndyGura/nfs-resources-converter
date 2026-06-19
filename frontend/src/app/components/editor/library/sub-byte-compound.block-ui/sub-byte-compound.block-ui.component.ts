import { ChangeDetectionStrategy, Component } from '@angular/core';
import { SubscribableGuiComponent } from '../../gui.component';

@Component({
  selector: 'app-sub-byte-compound-block-ui',
  templateUrl: './sub-byte-compound.block-ui.component.html',
  styleUrls: [],
  changeDetection: ChangeDetectionStrategy.OnPush,
  standalone: false,
})
export class SubByteCompoundBlockUiComponent extends SubscribableGuiComponent<{
  [key: string]: number | string | boolean;
}> {}
