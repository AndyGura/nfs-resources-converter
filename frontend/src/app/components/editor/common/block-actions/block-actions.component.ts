import { ChangeDetectorRef, Component, Input } from '@angular/core';
import { EelDelegateService } from '../../../../services/eel-delegate.service';
import { MainService } from '../../../../services/main.service';
import { ConfirmDialogComponent } from '../../../confirm.dialog/confirm.dialog.component';
import { firstValueFrom } from 'rxjs';
import { RunCustomActionDialogComponent } from '../../../run-custom-action.dialog/run-custom-action.dialog.component';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Resource, CustomAction } from '../../types';
import { lastIdPart } from '../../../../utils/join-id';

@Component({
  selector: 'app-block-actions',
  templateUrl: './block-actions.component.html',
  styleUrls: ['./block-actions.component.scss'],
})
export class BlockActionsComponent {
  @Input()
  public resource: Resource | null = null;

  constructor(
    readonly mainService: MainService,
    readonly eelDelegate: EelDelegateService,
    readonly cdr: ChangeDetectorRef,
    readonly dialog: MatDialog,
    private readonly snackBar: MatSnackBar,
  ) {}

  async serialize() {
    if (!this.resource) {
      return;
    }
    let resId = this.resource.id;
    let nameHint = lastIdPart(resId);
    // filter out delegate block internals
    while (nameHint == 'data') {
      resId = resId.substring(0, resId.length - nameHint.length);
      nameHint = lastIdPart(resId);
    }
    if (this.resource.schema.serialization.is_directory) {
      nameHint += '/'
    } else {
      nameHint += this.resource.schema.serialization.output_file_name_suffix || '';
    }
    let path = await this.eelDelegate.saveFileDialog(nameHint);
    if (!path) {
      return;
    }
    const files = await this.eelDelegate.serializeResource(this.resource.id, path, this.resource.schema.serialization.reversible_settings_patch);
    debugger;
    if (files && files.length > 0) {
      const commonPathPart = files.reduce((commonBeginning, currentString) => {
        let j = 0;
        while (j < commonBeginning.length && j < currentString.length && commonBeginning[j] === currentString[j]) {
          j++;
        }
        return commonBeginning.substring(0, j);
      });
      const lastSlashIndex = commonPathPart.lastIndexOf('/');
      const commonFolder = lastSlashIndex !== -1 ? commonPathPart.substring(0, lastSlashIndex) : commonPathPart;
      const snackBarRef = this.snackBar.open('Files exported', 'Open location', { duration: 10000 });
      snackBarRef.onAction().subscribe(() => {
        this.eelDelegate.openFileWithSystemApp(commonFolder);
      });
    }
    this.cdr.markForCheck();
  }

  async deserialize() {
    if (!this.resource) {
      return;
    }
    // TODO need to select more than one file, or directory
    let paths = await this.eelDelegate.openFileDialog();
    if (!paths) {
      return;
    }
    try {
      await this.mainService.deserializeResource(this.resource.id, [paths]);
    } finally {
      this.cdr.markForCheck();
    }
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
