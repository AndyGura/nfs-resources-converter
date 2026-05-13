import { Component } from '@angular/core';
import { ApiDelegateService } from '../../services/api/api-delegate.service';

@Component({
  selector: 'app-landing-page',
  templateUrl: './landing-page.component.html',
  styleUrls: ['./landing-page.component.scss'],
})
export class LandingPageComponent {
  constructor(public readonly api: ApiDelegateService) {}

  async openFile() {
    const fileNames = await this.api.openFileDialog();
    if (fileNames.length > 0) {
      await this.api.openFile(fileNames[0], true);
    }
  }

  async openRecentFile(path: string) {
    await this.api.openFile(path, true);
  }

  getFileName(path: string): string {
    if (!path) return '';
    const lastSlash = Math.max(path.lastIndexOf('/'), path.lastIndexOf('\\'));
    if (lastSlash === -1) return path;
    return path.substring(lastSlash + 1);
  }
}
