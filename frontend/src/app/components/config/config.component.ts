import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { EelDelegateService } from '../../services/eel-delegate.service';
import { MatSnackBar } from '@angular/material/snack-bar';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

@Component({
  selector: 'app-config',
  templateUrl: './config.component.html',
  styleUrls: ['./config.component.scss'],
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatCheckboxModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatDialogModule,
  ],
})
export class ConfigComponent implements OnInit {
  configForm: FormGroup;
  testingBlender = false;
  testingFFmpeg = false;
  blenderTestResult: { success: boolean; message: string } | null = null;
  ffmpegTestResult: { success: boolean; message: string } | null = null;

  constructor(
    private formBuilder: FormBuilder,
    private dialogRef: MatDialogRef<ConfigComponent>,
    private eelDelegate: EelDelegateService,
    private snackBar: MatSnackBar,
  ) {
    this.configForm = this.formBuilder.group({
      blender_executable: [''],
      ffmpeg_executable: [''],
      print_errors: [false],
      print_blender_log: [false],
    });
  }

  async ngOnInit() {
    const config = await this.eelDelegate.getGeneralConfig();
    this.configForm.patchValue(config);
  }

  async testBlenderPath() {
    this.testingBlender = true;
    this.blenderTestResult = null;
    try {
      this.blenderTestResult = await this.eelDelegate.testExecutable(this.configForm.get('blender_executable')?.value);
    } catch (error) {
      this.blenderTestResult = { success: false, message: 'Error testing Blender path' };
    } finally {
      this.testingBlender = false;
    }
  }

  async testFFmpegPath() {
    this.testingFFmpeg = true;
    this.ffmpegTestResult = null;
    try {
      this.ffmpegTestResult = await this.eelDelegate.testExecutable(this.configForm.get('ffmpeg_executable')?.value);
    } catch (error) {
      this.ffmpegTestResult = { success: false, message: 'Error testing FFmpeg path' };
    } finally {
      this.testingFFmpeg = false;
    }
  }

  async saveConfig() {
    try {
      await this.eelDelegate.patchGeneralConfig(this.configForm.value);
      this.snackBar.open('Configuration saved successfully', 'OK', { duration: 3000 });
      this.dialogRef.close();
    } catch (error) {
      this.snackBar.open('Error saving configuration', 'OK', { duration: 3000 });
    }
  }

  cancel() {
    this.dialogRef.close();
  }
}
