import { ChangeDetectionStrategy, ChangeDetectorRef, Component } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MainService } from './services/main.service';
import { MatDialog } from '@angular/material/dialog';
import { ConfirmDialogComponent } from './components/confirm.dialog/confirm.dialog.component';
import { firstValueFrom } from 'rxjs';
import { NavigationService } from './services/navigation.service';
import { ConverterComponent } from './components/converter/converter.component';
import { ConfigComponent } from './components/config/config.component';
import { environment } from '../environments/environment';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AppComponent {
  readonly isProduction = environment.production;

  constructor(
    readonly mainService: MainService,
    readonly dialog: MatDialog,
    readonly navigation: NavigationService,
    private readonly snackBar: MatSnackBar,
    private readonly cdr: ChangeDetectorRef,
  ) {}

  async openFile() {
    const fileNames = await this.mainService.api.openFileDialog();
    if (fileNames.length > 0) {
      await this.mainService.api.openFile(fileNames[0], true);
    }
  }

  async openRecentFile(path: string) {
    if (this.mainService.api.openedResourcePath$.getValue() === path) {
      return;
    }
    await this.mainService.api.openFile(path, true);
  }

  getFileName(path: string): string {
    if (!path) return '';
    const lastSlash = Math.max(path.lastIndexOf('/'), path.lastIndexOf('\\'));
    if (lastSlash === -1) return path;
    return path.substring(lastSlash + 1);
  }

  closeFile() {
    this.mainService.api.closeFile().then();
  }

  async saveResource() {
    try {
      await this.mainService.saveResource();
      this.snackBar.open('File Saved!', 'OK', { duration: 1500 });
    } catch (err: any) {
      this.snackBar.open('Error while saving file! ' + err.errorText, 'OK :(', { duration: 5000 });
    }
  }

  toggleUnknownsVisibility() {
    this.mainService.hideHiddenFields$.next(!this.mainService.hideHiddenFields$.getValue());
  }

  async reloadResource() {
    if (this.mainService.hasUnsavedChanges) {
      let dialogRef = this.dialog.open(ConfirmDialogComponent, {
        data: { text: 'There are unsaved changes, which will be lost. Are you sure you want to reload file?' },
      });
      if (!(await firstValueFrom(dialogRef.afterClosed()))) {
        return;
      }
    }
    await this.mainService.reloadResource();
    this.cdr.markForCheck();
  }

  openHomePage() {
    window.open('https://github.com/AndyGura/nfs-resources-converter', '_blank');
  }

  openDocs() {
    window.open('https://github.com/AndyGura/nfs-resources-converter/blob/main/resources/README.md', '_blank');
  }

  openBmac() {
    window.open('https://www.buymeacoffee.com/andygura', '_blank');
  }

  formatChangeId(id: string): string {
    const doubleUnderscoreIndex = id.lastIndexOf('__');
    if (doubleUnderscoreIndex === -1) {
      return id;
    }
    return id.substring(doubleUnderscoreIndex + 2);
  }

  getStagedChangesCount(changes: { [key: string]: any } | null): number {
    if (!changes) return 0;
    return Object.keys(changes).filter(key => key !== '__has_external_changes__').length;
  }

  openConverter() {
    this.dialog.open(ConverterComponent, {
      width: '800px',
      height: '600px',
      disableClose: true,
    });
  }

  openConfig() {
    this.dialog.open(ConfigComponent, {
      width: '600px',
      maxWidth: '90vw',
      maxHeight: '90vh',
      disableClose: true,
    });
  }
}
