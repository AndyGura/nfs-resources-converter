import { Injectable } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { firstValueFrom } from 'rxjs';
import { MainService } from './main.service';
import { CustomAction } from '../components/editor/types';
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

  async runCustomAction(
    resourceId: string,
    resourceName: string,
    action: CustomAction,
    formPatch: any = {},
    runImmediately: boolean = false,
  ): Promise<boolean> {
    if (runImmediately) {
      for (const { id } of action.args) {
        if (formPatch[id] === undefined) {
          runImmediately = false;
          break;
        }
      }
    }

    let args: any[] = [];
    if (!runImmediately) {
      const dialogRef = this.dialog.open(RunCustomActionDialogComponent, {
        data: { action, resourceName, formPatch },
      });
      const dialogArgs: any[] | undefined = await firstValueFrom(dialogRef.afterClosed());
      if (!dialogArgs) {
        return false;
      }
      args = dialogArgs;
    } else {
      args = formPatch;
    }
    try {
      await this.mainService.runCustomAction(resourceId, action, args);
      this.snackBar.open('Action performed!', 'OK', { duration: 1500 });
      return true;
    } catch (err: any) {
      await this.mainService.reloadResource();
      this.snackBar.open('Error while performing action! Reverting file state.. ' + (err.errorText || err), 'OK :(', {
        duration: 5000,
      });
      return false;
    }
  }
}
