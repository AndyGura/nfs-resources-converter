import { Component, Inject } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { CustomAction } from '../editor/types';

export interface RunCustomActionDialogData {
  action: CustomAction;
  resourceName: string;
}

@Component({
  selector: 'app-run-custom-action.dialog',
  templateUrl: './run-custom-action.dialog.component.html',
  styleUrls: ['./run-custom-action.dialog.component.scss'],
})
export class RunCustomActionDialogComponent {
  readonly argsForm: FormGroup;

  constructor(
    public dialogRef: MatDialogRef<RunCustomActionDialogComponent>,
    private fb: FormBuilder,
    @Inject(MAT_DIALOG_DATA) public data: RunCustomActionDialogData,
  ) {
    const formData: any = {};
    for (const arg of data.action.args) {
      const validators = [Validators.required];
      if (arg.type === 'number') {
        validators.push(Validators.pattern(/^\d+(\.\d+)?$/)); // Allow integers and decimals
      }
      let defaultValue = '';
      if (arg.type === 'file_output') {
        defaultValue = data.resourceName + arg.file_name_suffix;
      }
      formData[arg.id] = [defaultValue, validators];
    }
    this.argsForm = this.fb.group(formData);
  }

  submit() {
    const result = this.argsForm.value;
    for (const arg of this.data.action.args) {
      if (arg.type === 'number') {
        result[arg.id] = +result[arg.id];
      } else if (arg.type === 'file_output') {
        result[arg.id] = result[arg.id] || '';
      }
    }
    this.dialogRef.close(result);
  }

  getInputType(argType: string): string {
    switch (argType) {
      case 'number':
        return 'number';
      case 'string':
        return 'text';
      case 'file_output':
        return 'text'; // We'll use text input for file paths
      default:
        return 'text';
    }
  }
}
