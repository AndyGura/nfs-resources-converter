import { ChangeDetectionStrategy, Component, Inject, inject } from '@angular/core';
import { MainService } from '../../../../services/main.service';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { BlockData, BlockSchema } from '../../types';

export interface ArchiveItemEditDialogData {
  id: string;
  data: BlockData;
  schema: BlockSchema;
  name: string;
}

@Component({
  selector: 'app-archive-item-edit-dialog',
  templateUrl: './archive-item-edit.dialog.component.html',
  styleUrls: ['./archive-item-edit.dialog.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  standalone: false,
})
export class ArchiveItemEditDialogComponent {
  readonly mainService = inject(MainService);

  constructor(
    public dialogRef: MatDialogRef<ArchiveItemEditDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: ArchiveItemEditDialogData,
  ) {}
}
