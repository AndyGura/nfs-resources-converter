import { Component, Inject, ChangeDetectionStrategy } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { CustomAction } from '../editor/types';

export interface RunCustomActionDialogData {
  action: CustomAction;
  resourceName: string;
  formPatch?: any;
}

@Component({
  selector: 'app-run-custom-action.dialog',
  templateUrl: './run-custom-action.dialog.component.html',
  styleUrls: ['./run-custom-action.dialog.component.scss'],
  changeDetection: ChangeDetectionStrategy.Eager,
  standalone: false,
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
      if (data.formPatch?.[arg.id]) {
        formData[arg.id] = [data.formPatch[arg.id]];
        continue;
      }
      const validators = [Validators.required];
      if (arg.type === 'number') {
        validators.push(Validators.pattern(/^\d+(\.\d+)?$/)); // Allow integers and decimals
      }
      let defaultValue: string | boolean = '';
      if (arg.type === 'file_output') {
        defaultValue = data.resourceName + arg.file_name_suffix;
      } else if (arg.type === 'enum_string') {
        defaultValue = arg.choices[0] || '';
      } else if (arg.type === 'bool') {
        defaultValue = !!arg.default;
      } else if (arg.type === 'number') {
        defaultValue = arg.default === undefined ? '' : arg.default.toString();
      } else if (arg.type === 'string') {
        defaultValue = arg.default === undefined ? '' : arg.default;
      }
      formData[arg.id] = [defaultValue, validators];
    }
    this.argsForm = this.fb.group(formData);
  }

  submit() {
    const result = { ...(this.data.formPatch || {}), ...this.argsForm.value };
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
