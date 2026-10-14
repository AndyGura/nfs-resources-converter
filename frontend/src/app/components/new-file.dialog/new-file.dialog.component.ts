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
    { id: 'ffn', description: 'FFN font', iconBlockClass: 'FfnFont' },
    { id: 'fsh', description: 'FSH image archive', iconBlockClass: 'ShpiBlock' },
    { id: 'qfs', description: 'QFS image archive', iconBlockClass: 'ShpiBlock' },
    { id: 'pbs', description: 'PBS car physics (TNFS PC)', iconBlockClass: 'PlayerCarPhysics' },
    { id: 'pdn', description: 'PDN car AI and crash body (TNFS PC)', iconBlockClass: 'CarAiAndCrashBody' },
    { id: 'BigSpecsFam', description: 'BigSpecsFam car physics (TNFS 3DO)', iconBlockClass: 'PlayerCarPhysics' },
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
