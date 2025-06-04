import { ChangeDetectionStrategy, ChangeDetectorRef, Component } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSnackBar } from '@angular/material/snack-bar';
import { CommonModule } from '@angular/common';
import { EelDelegateService } from '../../services/eel-delegate.service';

declare const eel: any;

@Component({
  selector: 'app-converter',
  templateUrl: './converter.component.html',
  styleUrls: ['./converter.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatProgressBarModule,
  ],
})
export class ConverterComponent {
  converterForm: FormGroup;
  isConverting = false;
  outputPath = '';

  constructor(
    private fb: FormBuilder,
    public eelDelegate: EelDelegateService,
    private snackBar: MatSnackBar,
    private cdr: ChangeDetectorRef,
  ) {
    this.converterForm = this.fb.group({
      inputPath: ['', Validators.required],
      outputPath: ['', Validators.required],
    });
  }

  async selectInputDirectory(): Promise<void> {
    const directory = await this.eelDelegate.selectDirectoryDialog();
    if (directory) {
      this.converterForm.get('inputPath')?.setValue(directory);
      this.cdr.markForCheck();
    }
  }

  async selectOutputDirectory(): Promise<void> {
    const directory = await this.eelDelegate.selectDirectoryDialog();
    if (directory) {
      this.converterForm.get('outputPath')?.setValue(directory);
      this.cdr.markForCheck();
    }
  }

  async openOutputDirectory(): Promise<void> {
    if (this.outputPath) {
      const result = await this.eelDelegate.startFile(this.outputPath);
      if (!result.success) {
        this.snackBar.open(`Failed to open directory: ${result.error}`, 'OK', { duration: 5000 });
      }
    }
  }

  async convertFiles(): Promise<void> {
    if (this.converterForm.invalid) {
      return;
    }

    this.isConverting = true;
    this.eelDelegate.conversionProgress$.next([0, 0]);
    this.cdr.markForCheck();

    try {
      const result = await this.eelDelegate.convertFiles(
        this.converterForm.get('inputPath')?.value,
        this.converterForm.get('outputPath')?.value,
      );

      if (result.success) {
        this.outputPath = result.output_path || this.converterForm.get('outputPath')?.value;
        this.snackBar
          .open('Conversion completed successfully!', 'Open Directory', {
            duration: 5000,
          })
          .onAction()
          .subscribe(() => {
            this.openOutputDirectory();
          });

        // Automatically open the output directory
        this.openOutputDirectory();
      } else {
        this.snackBar.open(`Conversion failed: ${result.error}`, 'OK', { duration: 5000 });
      }
    } catch (error) {
      this.snackBar.open(`An error occurred: ${error}`, 'OK', { duration: 5000 });
    } finally {
      this.isConverting = false;
      this.cdr.markForCheck();
    }
  }
}
