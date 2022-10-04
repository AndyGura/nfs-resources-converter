import { Component, Inject, } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';

@Component({
  selector: 'app-run-custom-action.dialog',
  templateUrl: './run-custom-action.dialog.component.html',
  styleUrls: ['./run-custom-action.dialog.component.scss']
})
export class RunCustomActionDialogComponent {

  readonly argsForm: FormGroup;

  constructor(
    public dialogRef: MatDialogRef<RunCustomActionDialogComponent>,
    private fb: FormBuilder,
    @Inject(MAT_DIALOG_DATA) public data: CustomAction,
  ) {
    const formData: any = {};
    for (const arg of data.args) {
      formData[arg.id] = ['', Validators.required];
    }
    this.argsForm = this.fb.group(formData);
  }

  submit() {
    const result = this.argsForm.value;
    for (const arg of this.data.args) {
      if (arg.type == 'number') {
        result[arg.id] = +result[arg.id];
      }
    }
    this.dialogRef.close(result);
  }

}
