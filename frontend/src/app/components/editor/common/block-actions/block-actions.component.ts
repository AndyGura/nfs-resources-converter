import { ChangeDetectorRef, Component, Input } from '@angular/core';
import { MainService } from '../../../../services/main.service';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Resource, CustomAction } from '../../types';
import { lastIdPart } from '../../../../utils/join-id';
import { CustomActionService } from '../../../../services/custom-action.service';

@Component({
  selector: 'app-block-actions',
  templateUrl: './block-actions.component.html',
  styleUrls: ['./block-actions.component.scss'],
})
export class BlockActionsComponent {
  @Input()
  public resource: Resource | null = null;

  @Input()
  public hideCustomActions = false;

  constructor(
    readonly mainService: MainService,
    readonly cdr: ChangeDetectorRef,
    private readonly customActionService: CustomActionService,
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
      nameHint += '/';
    } else {
      nameHint += this.resource.schema.serialization.output_file_name_suffix || '';
    }
    let path = await this.mainService.api.saveFileDialog(nameHint);
    if (!path) {
      return;
    }
    const files = await this.mainService.api.serializeResource(
      this.resource.id,
      path,
      this.resource.schema.serialization.reversible_settings_patch,
    );
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
        this.mainService.api.openFileWithSystemApp(commonFolder);
      });
    }
    this.cdr.markForCheck();
  }

  async deserialize() {
    if (!this.resource) {
      return;
    }
    // TODO need a way to select directory?
    let paths = await this.mainService.api.openFileDialog(true);
    if (!paths) {
      return;
    }
    try {
      await this.mainService.deserializeResource(this.resource.id, paths);
    } finally {
      this.cdr.markForCheck();
    }
  }

  async runCustomAction(action: CustomAction) {
    if (!this.resource) {
      return;
    }
    await this.customActionService.runCustomAction(this.resource.id, this.resource.name, action);
    this.cdr.markForCheck();
  }
}
