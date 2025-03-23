import { ChangeDetectionStrategy, ChangeDetectorRef, Component } from '@angular/core';
import { EelDelegateService } from './services/eel-delegate.service';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MainService } from './services/main.service';
import { MatDialog } from '@angular/material/dialog';
import { ConfirmDialogComponent } from './components/confirm.dialog/confirm.dialog.component';
import { firstValueFrom } from 'rxjs';
import { NavigationService } from './services/navigation.service';

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
}
