import { Component } from '@angular/core';

@Component({
  selector: 'app-fallback.block-ui',
  templateUrl: './fallback.block-ui.component.html',
  styleUrls: ['./fallback.block-ui.component.scss']
})
export class FallbackBlockUiComponent {

  resourceData: ReadData | null = null;

  constructor() {
  }

}
