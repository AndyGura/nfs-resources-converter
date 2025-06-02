import { ChangeDetectionStrategy, ChangeDetectorRef, Component } from '@angular/core';
import { EelDelegateService } from './services/eel-delegate.service';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MainService } from './services/main.service';
import { MatDialog } from '@angular/material/dialog';
import { ConfirmDialogComponent } from './components/confirm.dialog/confirm.dialog.component';
import { firstValueFrom } from 'rxjs';
import { NavigationService } from './services/navigation.service';
import { ConverterComponent } from './components/converter/converter.component';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AppComponent {
  constructor(
    readonly eelDelegate: EelDelegateService,
    readonly mainService: MainService,
    readonly dialog: MatDialog,
    readonly navigation: NavigationService,
    private readonly snackBar: MatSnackBar,
    private readonly cdr: ChangeDetectorRef,
  ) {}

  async openFile() {
    const fileName = await this.eelDelegate.openFileDialog();
    if (fileName) {
      await this.eelDelegate.openFile(fileName, true);
    }
  }

  closeFile() {
    this.eelDelegate.openedResource$.next(null);
    this.eelDelegate.openedResourcePath$.next(null);
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

  openConverter() {
    const dialogRef = this.dialog.open(ConverterComponent, {
      width: '800px',
      height: '600px',
    });
  }
}
