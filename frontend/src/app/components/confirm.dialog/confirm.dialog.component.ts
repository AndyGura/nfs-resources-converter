import { Component, Inject, ChangeDetectionStrategy } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';

@Component({
  selector: 'app-confirm.dialog',
  templateUrl: './confirm.dialog.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  standalone: false,
})
export class ConfirmDialogComponent {
  constructor(
    public dialogRef: MatDialogRef<ConfirmDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: { text: string },
  ) {}
}
