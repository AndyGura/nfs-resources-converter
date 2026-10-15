import { ChangeDetectionStrategy, Component, EventEmitter, inject, Input, Output } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';
import { PrimitiveGuiComponent } from '../../gui.component';
import { BlockSchema } from '../../types';

@Component({
  selector: 'app-string-block-ui',
  templateUrl: './string.block-ui.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  standalone: false,
})
export class StringBlockUiComponent extends PrimitiveGuiComponent<string> {
  override get resourceSchema(): BlockSchema | undefined {
    return super.resourceSchema;
  }

  @Input()
  override set resourceSchema(value: BlockSchema | undefined) {
    super.resourceSchema = value;
    if (!isNaN(+this.resourceSchema?.length)) {
      this.minLength = this.maxLength = +this.resourceSchema?.length;
    }
  }

  @Output('changed') changed: EventEmitter<string> = new EventEmitter<string>();

  minLength: number | null = null;
  maxLength: number | null = null;

  private readonly snackBar = inject(MatSnackBar);

  // a fixed-size field holds `maxLength` bytes of UTF-8: a character outside ASCII takes 2..4
  onTextSet(input: HTMLInputElement) {
    const value = input.value;
    const bytes = new TextEncoder().encode(value).length;
    if (this.maxLength !== null && bytes > this.maxLength) {
      this.snackBar.open(
        `${this.resourceName || 'Value'} holds ${this.maxLength} bytes: "${value}" is ${bytes}`,
        'OK',
        { duration: 6000 },
      );
      input.value = this.resourceData ?? '';
      return;
    }
    this.onValueSet(value);
  }
}
