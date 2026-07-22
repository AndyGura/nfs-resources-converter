import { ChangeDetectionStrategy, Component } from '@angular/core';
import { SubscribableGuiComponent } from '../../gui.component';

@Component({
  selector: 'targa-image-block-ui',
  templateUrl: './targa-image.block-ui.component.html',
  styleUrls: ['./targa-image.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  standalone: false,
})
export class TargaImageBlockUiComponent extends SubscribableGuiComponent {}
