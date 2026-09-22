import { Component, Inject, ChangeDetectionStrategy } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { FormBuilder, FormGroup, ValidatorFn, Validators } from '@angular/forms';
import { CustomAction, CustomActionArgument } from '../editor/types';
import { MainService } from '../../services/main.service';
import { lastIdPart } from '../../utils/join-id';

export interface RunCustomActionDialogData {
  action: CustomAction;
  resourceId: string;
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

  // Validators an arg would carry if unconditionally required, keyed by arg id.
  private readonly argValidators = new Map<string, ValidatorFn[]>();

  constructor(
    public dialogRef: MatDialogRef<RunCustomActionDialogComponent>,
    private fb: FormBuilder,
    @Inject(MAT_DIALOG_DATA) public data: RunCustomActionDialogData,
    private mainService: MainService,
  ) {
    const formData: any = {};
    for (const arg of data.action.args) {
      if (data.formPatch?.[arg.id]) {
        formData[arg.id] = [data.formPatch[arg.id]];
        continue;
      }
      const validators: ValidatorFn[] = [Validators.required];
      if (arg.type === 'number') {
        validators.push(Validators.pattern(/^\d+(\.\d+)?$/)); // Allow integers and decimals
      }
      this.argValidators.set(arg.id, validators);
      let defaultValue: string | boolean = '';
      if (arg.type === 'enum_string') {
        defaultValue = arg.default || arg.choices[0] || '';
      } else if (arg.type === 'bool') {
        defaultValue = !!arg.default;
      } else if (arg.type === 'number') {
        defaultValue = arg.default === undefined ? '' : arg.default.toString();
      } else if (arg.type === 'string') {
        defaultValue = arg.default === undefined ? '' : arg.default;
      }
      formData[arg.id] = [defaultValue, arg.visible_when ? [] : validators];
    }
    this.argsForm = this.fb.group(formData);
    this.updateConditionalValidators();
    this.argsForm.valueChanges.subscribe(() => this.updateConditionalValidators());
  }

  isArgVisible(arg: CustomActionArgument): boolean {
    return !arg.visible_when || this.argsForm.get(arg.visible_when.arg)?.value === arg.visible_when.value;
  }

  // Keeps hidden `visible_when`-gated controls out of the validity check.
  private updateConditionalValidators(): void {
    for (const arg of this.data.action.args) {
      if (!arg.visible_when) continue;
      const control = this.argsForm.get(arg.id);
      if (!control) continue;
      control.setValidators(this.isArgVisible(arg) ? (this.argValidators.get(arg.id) ?? null) : null);
      control.updateValueAndValidity({ emitEvent: false });
    }
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

  async selectOutputFile(arg: CustomActionArgument) {
    if (arg.type === 'file_output') {
      let resId = this.data.resourceId;
      let nameHint = lastIdPart(resId);
      // filter out delegate block internals
      while (nameHint == 'data') {
        resId = resId.substring(0, resId.length - nameHint.length);
        nameHint = lastIdPart(resId);
      }
      nameHint += arg.file_name_suffix || '';
      const path = await this.mainService.api.saveFileDialog(nameHint);
      if (path) {
        this.argsForm.get(arg.id)?.setValue(path);
      }
    }
  }
}
