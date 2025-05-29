import { Component } from '@angular/core';
import { EelDelegateService } from '../../services/eel-delegate.service';

@Component({
  selector: 'app-landing-page',
  templateUrl: './landing-page.component.html',
  styleUrls: ['./landing-page.component.scss'],
})
export class LandingPageComponent {
  constructor(private readonly eelDelegate: EelDelegateService) {}

  async openFile() {
    const fileName = await this.eelDelegate.openFileDialog();
    if (fileName) {
      await this.eelDelegate.openFile(fileName, true);
    }
  }
}
