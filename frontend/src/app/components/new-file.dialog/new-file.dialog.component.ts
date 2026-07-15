import { Component, ChangeDetectionStrategy } from '@angular/core';
import { MatDialogRef } from '@angular/material/dialog';
import { fileFormatIcon } from '../../utils/file-format-icon';

@Component({
  selector: 'app-new-file.dialog',
  templateUrl: './new-file.dialog.component.html',
  styleUrls: ['./new-file.dialog.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  standalone: false,
})
export class NewFileDialogComponent {
  public formats = [
    { id: 'ffn', name: 'FFN font', blockClass: 'FfnFont' },
    { id: 'fsh', name: 'FSH image archive', blockClass: 'ShpiBlock' },
  ];
  public selectedFormat = 'ffn';

  constructor(public dialogRef: MatDialogRef<NewFileDialogComponent>) {}

  onCancel(): void {
    this.dialogRef.close();
  }

  onCreate(): void {
    this.dialogRef.close(this.selectedFormat);
  }

  fileFormatIcon = fileFormatIcon;
}
