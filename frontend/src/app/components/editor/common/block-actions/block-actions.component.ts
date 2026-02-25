import { ChangeDetectorRef, Component, Input } from '@angular/core';
import { EelDelegateService } from '../../../../services/eel-delegate.service';
import { MainService } from '../../../../services/main.service';
import { ConfirmDialogComponent } from '../../../confirm.dialog/confirm.dialog.component';
import { firstValueFrom } from 'rxjs';
import { RunCustomActionDialogComponent } from '../../../run-custom-action.dialog/run-custom-action.dialog.component';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Resource, CustomAction } from '../../types';

@Component({
  selector: 'app-block-actions',
  templateUrl: './block-actions.component.html',
  styleUrls: ['./block-actions.component.scss'],
})
export class BlockActionsComponent {
  @Input()
  public resource: Resource | null = null;

  isInReversibleSerializationState = false;

  constructor(
    readonly mainService: MainService,
    readonly eelDelegate: EelDelegateService,
    readonly cdr: ChangeDetectorRef,
    readonly dialog: MatDialog,
    private readonly snackBar: MatSnackBar,
  ) {}

  async serializeBlockReversible() {
    if (!this.resource) {
      return;
    }
    // TODO get local changes
    const [files, isReversible] = await this.eelDelegate.serializeReversible(this.resource.id, []);
    const commonPathPart = files.reduce((commonBeginning, currentString) => {
      let j = 0;
      while (j < commonBeginning.length && j < currentString.length && commonBeginning[j] === currentString[j]) {
        j++;
      }
      return commonBeginning.substring(0, j);
    });
    await this.eelDelegate.openFileWithSystemApp(commonPathPart);
    this.isInReversibleSerializationState = isReversible;
    this.cdr.markForCheck();
  }

  async deserialize() {
    if (!this.resource) {
      return;
    }
    await this.mainService.deserializeResource(this.resource.id);
    this.isInReversibleSerializationState = false;
    this.cdr.markForCheck();
  }

  async runCustomAction(action: CustomAction) {
    if (this.mainService.hasUnsavedChanges) {
      let dialogRef = this.dialog.open(ConfirmDialogComponent, {
        data: { text: 'Cannot run custom action on a file with not saved changes. Do you want to save them first?' },
      });
      if (!(await firstValueFrom(dialogRef.afterClosed()))) {
        return;
      }
      try {
        await this.mainService.saveResource();
        this.snackBar.open('File Saved!', 'OK', { duration: 1500 });
      } catch (err: any) {
        this.snackBar.open('Error while saving file! ' + err.errorText, 'OK :(', { duration: 5000 });
      }
    }
    let dialogRef = this.dialog.open(RunCustomActionDialogComponent, {
      data: {
        action: action,
        resourceName: this.resource?.name || ''
      },
    });
    const args: any[] | undefined = await firstValueFrom(dialogRef.afterClosed());
    if (!args) {
      return;
    }
    try {
      await this.mainService.runCustomAction(this.resource!.id, action, args);
      this.snackBar.open('Action performed!', 'OK', { duration: 1500 });
    } catch (err: any) {
      this.mainService.clearUnsavedChanges();
      this.mainService.reloadResource().then(() => this.cdr.markForCheck());
      this.snackBar.open('Error while performing action! Reverting file state.. ' + err.errorText || err, 'OK :(', {
        duration: 5000,
      });
    }
  }
}
