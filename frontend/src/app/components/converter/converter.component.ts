import { ChangeDetectionStrategy, ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSnackBar } from '@angular/material/snack-bar';
import { CommonModule } from '@angular/common';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatDividerModule } from '@angular/material/divider';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatIconModule } from '@angular/material/icon';
import { MatDialog, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { EelDelegateService } from '../../services/eel-delegate.service';
import { ConfigComponent } from '../config/config.component';
import { firstValueFrom } from 'rxjs';

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
    MatCheckboxModule,
    MatExpansionModule,
    MatDividerModule,
    MatTooltipModule,
    MatIconModule,
    MatDialogModule,
  ],
})
export class ConverterComponent implements OnInit {
  converterForm: FormGroup;
  isConverting = false;
  outputPath = '';
  configLoaded = false;
  blenderExecutablePath = '';
  isBlenderWorking = false;
  isTestingBlender = false;

  constructor(
    private fb: FormBuilder,
    public eelDelegate: EelDelegateService,
    private snackBar: MatSnackBar,
    private cdr: ChangeDetectorRef,
    private dialog: MatDialog,
    private dialogRef: MatDialogRef<ConfigComponent>,
  ) {
    this.converterForm = this.fb.group({
      input_path: ['', Validators.required],
      output_path: ['', Validators.required],
      multiprocess_processes_count: [0],
      images__save_images_only: [false],
      maps__save_as_chunked: [false],
      maps__save_invisible_wall_collisions: [false],
      maps__save_terrain_collisions: [false],
      maps__save_spherical_skybox_texture: [true],
      maps__add_props_to_obj: [true],
      geometry__save_obj: [true],
      geometry__save_blend: [true],
      geometry__export_to_gg_web_engine: [false],
    });
  }

  async ngOnInit(): Promise<void> {
    await this.loadConfig();
    await this.testBlenderExecutable();
  }

  async testBlenderExecutable(): Promise<void> {
    this.isTestingBlender = true;
    this.cdr.markForCheck();

    try {
      const result = await this.eelDelegate.testExecutable(this.blenderExecutablePath);
      this.isBlenderWorking = result.success;

      // If Blender is not working, disable the related options
      if (!this.isBlenderWorking) {
        const geometryGroup = this.converterForm.get('geometry');
        if (geometryGroup) {
          geometryGroup.get('save_blend')?.disable();
          geometryGroup.get('export_to_gg_web_engine')?.disable();
        }
      }
    } catch (error) {
      this.isBlenderWorking = false;
      console.error('Error testing Blender executable:', error);
    } finally {
      this.isTestingBlender = false;
      this.cdr.markForCheck();
    }
  }

  openConfigDialog(): void {
    const dialogRef = this.dialog.open(ConfigComponent, {
      width: '600px',
      maxWidth: '90vw',
      maxHeight: '90vh',
      disableClose: true,
    });
    firstValueFrom(dialogRef.afterClosed()).then(async () => {
      await this.loadConfig();
      await this.testBlenderExecutable();
    });
  }

  async loadConfig(): Promise<void> {
    try {
      const generalConfig = await this.eelDelegate.getGeneralConfig();
      const conversionConfig = await this.eelDelegate.getConversionConfig();
      this.blenderExecutablePath = generalConfig.blender_executable;
      this.converterForm.patchValue(conversionConfig);
      this.configLoaded = true;
      this.cdr.markForCheck();
    } catch (error) {
      console.error('Failed to load config:', error);
      this.snackBar.open('Failed to load configuration settings', 'OK', { duration: 5000 });
    }
  }

  async selectInputDirectory(): Promise<void> {
    const directory = await this.eelDelegate.selectDirectoryDialog();
    if (directory) {
      this.converterForm.get('input_path')?.setValue(directory);
      this.cdr.markForCheck();
    }
  }

  async selectOutputDirectory(): Promise<void> {
    const directory = await this.eelDelegate.selectDirectoryDialog();
    if (directory) {
      this.converterForm.get('output_path')?.setValue(directory);
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
    let conversionConfig = await this.eelDelegate.patchConversionConfig(this.converterForm.value);
    this.isConverting = true;
    this.converterForm.disable();
    this.eelDelegate.conversionProgress$.next([0, 0]);
    this.cdr.markForCheck();
    try {
      const result = await this.eelDelegate.convertFiles(
        conversionConfig.input_path,
        conversionConfig.output_path,
        this.converterForm.value,
      );
      if (result.success) {
        this.outputPath = conversionConfig.output_path;
        this.snackBar
          .open('Conversion completed successfully!', 'Open Directory', {
            duration: 5000,
          })
          .onAction()
          .subscribe(() => {
            this.openOutputDirectory();
          });
        this.openOutputDirectory().then();
      } else {
        this.snackBar.open(`Conversion failed: ${result.error}`, 'OK', { duration: 5000 });
      }
    } catch (error) {
      this.snackBar.open(`An error occurred: ${error}`, 'OK', { duration: 5000 });
    } finally {
      this.isConverting = false;
      this.converterForm.enable();
      this.cdr.markForCheck();
    }
  }

  cancel() {
    this.dialogRef.close();
  }
}
