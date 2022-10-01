import { ChangeDetectionStrategy, ChangeDetectorRef, Component } from '@angular/core';
import { EelDelegateService } from './services/eel-delegate.service';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MainService } from './services/main.service';
import { MatDialog } from '@angular/material/dialog';
import { ConfirmDialogComponent } from './components/confirm.dialog/confirm.dialog.component';
import { firstValueFrom } from 'rxjs';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AppComponent {

  constructor(readonly eelDelegate: EelDelegateService,
              readonly mainService: MainService,
              readonly dialog: MatDialog,
              private readonly snackBar: MatSnackBar,
              private readonly cdr: ChangeDetectorRef) {
  }

  async saveResource() {
    try {
      const changes = Object.entries(this.mainService.changedDataBlocks);
      await this.eelDelegate.saveFile(changes.map(([id, value]) => {
        return { id, value };
      }));
      Object.keys(this.mainService.changedDataBlocks).forEach(key => {
        delete this.mainService.changedDataBlocks[key];
      });
      this.snackBar.open('File Saved!', 'OK', { duration: 1500 });
    } catch (err: any) {
      this.snackBar.open('Error while saving file! ' + err.errorText, 'OK :(', { duration: 1500 });
    }
  }

  async reloadResource() {
    if (this.mainService.hasUnsavedChanges) {
      let dialogRef = this.dialog.open(ConfirmDialogComponent, {
        data: { text: 'There are unsaved changes, which will be lost. Are you sure you want to reload file?' }
      });
      if (!(await firstValueFrom(dialogRef.afterClosed()))) {
        return;
      }
    }
    const path = this.mainService.eelDelegate.openedResourcePath$.getValue();
    if (path) {
      this.eelDelegate.openFile(path, true).then();
    }
    this.cdr.markForCheck();
  }

}
