import { Component, ChangeDetectionStrategy } from '@angular/core';
import { ApiDelegateService } from '../../services/api-delegate.service';

import { MatDialog } from '@angular/material/dialog';
import { firstValueFrom } from 'rxjs';
import { NewFileDialogComponent } from '../new-file.dialog/new-file.dialog.component';

@Component({
  selector: 'app-landing-page',
  templateUrl: './landing-page.component.html',
  styleUrls: ['./landing-page.component.scss'],
  changeDetection: ChangeDetectionStrategy.Eager,
  standalone: false,
})
export class LandingPageComponent {
  constructor(
    public readonly api: ApiDelegateService,
    private readonly dialog: MatDialog,
  ) {}

  async openFile() {
    const fileNames = await this.api.openFileDialog();
    if (fileNames.length > 0) {
      await this.api.openFile(fileNames[0], true);
    }
  }

  async createNewFile() {
    const dialogRef = this.dialog.open(NewFileDialogComponent, {
      width: '400px',
    });
    const format = await firstValueFrom(dialogRef.afterClosed());
    if (format) {
      const path = await this.api.saveFileDialog(`Untitled.${format}`);
      if (path) {
        await this.api.createNewFile(path, format);
      }
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
