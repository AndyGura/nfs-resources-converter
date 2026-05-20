import { Injectable } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { firstValueFrom } from 'rxjs';
import { MainService } from './main.service';
import { CustomAction, Resource } from '../components/editor/types';
import { ConfirmDialogComponent } from '../components/confirm.dialog/confirm.dialog.component';
import { RunCustomActionDialogComponent } from '../components/run-custom-action.dialog/run-custom-action.dialog.component';

@Injectable({
  providedIn: 'root',
})
export class CustomActionService {
  constructor(
    private readonly mainService: MainService,
    private readonly dialog: MatDialog,
    private readonly snackBar: MatSnackBar,
  ) {}

  async runCustomAction(resourceId: string, resourceName: string, action: CustomAction): Promise<boolean> {
    if (this.mainService.hasUnsavedChanges) {
      const dialogRef = this.dialog.open(ConfirmDialogComponent, {
        data: { text: 'Cannot run custom action on a file with not saved changes. Do you want to save them first?' },
      });
      const result = await firstValueFrom(dialogRef.afterClosed());
      if (result === undefined) {
        return false;
      }
      if (result) {
        try {
          await this.mainService.saveResource();
          this.snackBar.open('File Saved!', 'OK', { duration: 1500 });
        } catch (err: any) {
          this.snackBar.open('Error while saving file! ' + err.errorText, 'OK :(', { duration: 5000 });
          return false;
        }
      }
    }

    const dialogRef = this.dialog.open(RunCustomActionDialogComponent, {
      data: {
        action: action,
        resourceName,
      },
    });

    const args: any[] | undefined = await firstValueFrom(dialogRef.afterClosed());
    if (!args) {
      return false;
    }

    try {
      await this.mainService.runCustomAction(resourceId, action, args);
      this.snackBar.open('Action performed!', 'OK', { duration: 1500 });
      return true;
    } catch (err: any) {
      this.mainService.clearUnsavedChanges();
      await this.mainService.reloadResource();
      this.snackBar.open('Error while performing action! Reverting file state.. ' + (err.errorText || err), 'OK :(', {
        duration: 5000,
      });
      return false;
    }
  }
}
