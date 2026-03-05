import { Component } from '@angular/core';
import { EelDelegateService } from '../../services/eel-delegate.service';

@Component({
  selector: 'app-landing-page',
  templateUrl: './landing-page.component.html',
  styleUrls: ['./landing-page.component.scss'],
})
export class LandingPageComponent {
  constructor(public readonly eelDelegate: EelDelegateService) {}

  async openFile() {
    const fileName = await this.eelDelegate.openFileDialog();
    if (fileName) {
      await this.eelDelegate.openFile(fileName, true);
    }
  }

  async openRecentFile(path: string) {
    await this.eelDelegate.openFile(path, true);
  }

  getFileName(path: string): string {
    if (!path) return '';
    const lastSlash = Math.max(path.lastIndexOf('/'), path.lastIndexOf('\\'));
    if (lastSlash === -1) return path;
    return path.substring(lastSlash + 1);
  }
}
