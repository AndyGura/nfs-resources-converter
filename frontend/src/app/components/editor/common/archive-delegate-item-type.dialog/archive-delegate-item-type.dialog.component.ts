import { Component, ChangeDetectionStrategy, Inject } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { BlockSchema } from '../../types';
import { fileFormatIcon } from '../../../../utils/file-format-icon';

@Component({
  selector: 'app-archive-delegate-item-type.dialog',
  templateUrl: './archive-delegate-item-type.dialog.component.html',
  styleUrls: ['./archive-delegate-item-type.dialog.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  standalone: false,
})
export class ArchiveDelegateItemTypeDialogComponent {
  public selectedIndex = 0;

  constructor(
    public dialogRef: MatDialogRef<ArchiveDelegateItemTypeDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: { schemas: BlockSchema[] },
  ) {}

  onCancel(): void {
    this.dialogRef.close();
  }

  onSelect(): void {
    this.dialogRef.close(this.selectedIndex);
  }

  fileFormatIcon = fileFormatIcon;

  getSchemaName(schema: BlockSchema): string {
    return schema.block_class_mro.split('__')[0];
  }
}
