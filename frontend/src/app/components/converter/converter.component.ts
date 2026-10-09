import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  DestroyRef,
  ElementRef,
  OnDestroy,
  OnInit,
  ViewChild,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import {
  AbstractControl,
  FormBuilder,
  FormControl,
  FormGroup,
  ReactiveFormsModule,
  ValidationErrors,
  Validators,
} from '@angular/forms';
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
import { MatSelectModule } from '@angular/material/select';
import { ErrorStateMatcher } from '@angular/material/core';
import { ApiDelegateService } from '../../services/api/api-delegate.service';
import { ConversionConfig, ConversionPresets } from '../../services/api/api-types';
import { ConfigComponent } from '../config/config.component';
import { firstValueFrom } from 'rxjs';

// mirrors config.py: CONVERSION_PRESET_NAME_PATTERN, CONVERSION_PRESET_NAME_MAX_LENGTH, NO_PRESET_NAME
const PRESET_NAME_PATTERN = /^[A-Za-z0-9](?:[A-Za-z0-9 _.\-]*[A-Za-z0-9])?$/;
const PRESET_NAME_MAX_LENGTH = 64;
const NO_PRESET_NAME = 'No preset';
// delay of saving edited settings to the selected preset
const SETTINGS_SAVE_DELAY_MS = 300;

@Component({
  selector: 'app-converter',
  templateUrl: './converter.component.html',
  styleUrls: ['./converter.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
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
    MatSelectModule,
  ],
})
export class ConverterComponent implements OnInit, OnDestroy {
  converterForm: FormGroup;
  isConverting = false;
  outputPath = '';
  configLoaded = false;
  blenderExecutablePath = '';
  isBlenderWorking = false;
  isTestingBlender = false;

  readonly noPresetName = NO_PRESET_NAME;
  presets: string[] = [];
  // null = no preset (default settings)
  selectedPreset: string | null = null;
  // non-null while a new preset name is being entered
  newPresetName: FormControl<string> | null = null;
  readonly showErrorWhileTyping: ErrorStateMatcher = {
    isErrorState: control => !!control && control.invalid && control.dirty,
  };
  settingsExpanded = false;
  isUpdatingPresets = false;

  @ViewChild('newPresetInput') set newPresetInput(input: ElementRef<HTMLInputElement> | undefined) {
    input?.nativeElement.focus();
  }

  // settings edited in place, waiting to be saved to the preset that was selected when they changed
  private pendingSettingsSave: { preset: string | null; values: Partial<ConversionConfig> } | null = null;
  private settingsSaveTimer: ReturnType<typeof setTimeout> | null = null;

  constructor(
    private fb: FormBuilder,
    public api: ApiDelegateService,
    private snackBar: MatSnackBar,
    private cdr: ChangeDetectorRef,
    private dialog: MatDialog,
    private dialogRef: MatDialogRef<ConfigComponent>,
    private destroyRef: DestroyRef,
  ) {
    this.converterForm = this.fb.group({
      input_path: ['', Validators.required],
      output_path: ['', Validators.required],
      multiprocess_processes_count: [0],
      images__save_image_positions: [false],
      images__save_palettes: [false],
      images__save_mipmaps: [false],
      images__save_embedded_palette: [false],
      images__save_texts: [false],
      maps__save_as_chunked: [false],
      maps__save_invisible_wall_collisions: [false],
      maps__save_terrain_collisions: [false],
      maps__save_spherical_skybox_texture: [true],
      maps__add_props_to_obj: [true],
      geometry__save_obj: [true],
      geometry__save_blend: [true],
      geometry__export_to_gg_web_engine: [false],
    });
    // every form control is a setting of the selected preset
    this.converterForm.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => {
      if (this.configLoaded && this.converterForm.enabled) {
        this.scheduleSettingsSave();
      }
    });
  }

  async ngOnInit(): Promise<void> {
    await this.loadConfig();
    await this.testBlenderExecutable();
  }

  ngOnDestroy(): void {
    this.flushSettingsSave().then();
  }

  async testBlenderExecutable(): Promise<void> {
    this.isTestingBlender = true;
    this.cdr.markForCheck();

    try {
      const result = await this.api.testExecutable(this.blenderExecutablePath);
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
      await this.flushSettingsSave();
      const generalConfig = await this.api.getGeneralConfig();
      this.applyPresets(await this.api.getConversionPresets());
      const conversionConfig = await this.api.getConversionConfig(this.selectedPreset);
      this.blenderExecutablePath = generalConfig.blender_executable;
      this.converterForm.patchValue(conversionConfig, { emitEvent: false });
      this.configLoaded = true;
      this.cdr.markForCheck();
    } catch (error) {
      console.error('Failed to load config:', error);
      this.snackBar.open('Failed to load configuration settings', 'OK', { duration: 5000 });
    }
  }

  async selectInputDirectory(): Promise<void> {
    const directory = await this.api.selectDirectoryDialog();
    if (directory) {
      this.converterForm.get('input_path')?.setValue(directory);
      this.cdr.markForCheck();
    }
  }

  async selectOutputDirectory(): Promise<void> {
    const directory = await this.api.selectDirectoryDialog();
    if (directory) {
      this.converterForm.get('output_path')?.setValue(directory);
      this.cdr.markForCheck();
    }
  }

  async openOutputDirectory(): Promise<void> {
    if (this.outputPath) {
      const result = await this.api.openFileWithSystemApp(this.outputPath);
      if (!result.success) {
        this.snackBar.open(`Failed to open directory: ${result.error}`, 'OK', { duration: 5000 });
      }
    }
  }

  async convertFiles(): Promise<void> {
    if (this.converterForm.invalid) {
      return;
    }
    await this.flushSettingsSave();
    const conversionConfig = await this.api.patchConversionConfig(this.presetSettingsValue(), this.selectedPreset);
    this.isConverting = true;
    this.converterForm.disable({ emitEvent: false });
    this.api.conversionProgress$.next([0, 0]);
    this.cdr.markForCheck();
    try {
      const result = await this.api.convertFiles(
        conversionConfig.input_path,
        conversionConfig.output_path,
        conversionConfig,
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
      this.converterForm.enable({ emitEvent: false });
      this.cdr.markForCheck();
    }
  }

  cancel() {
    this.dialogRef.close();
  }

  async selectPreset(preset: string | null): Promise<void> {
    await this.runPresetsUpdate(async () => {
      await this.flushSettingsSave();
      this.applyPresets(await this.api.selectConversionPreset(preset));
      await this.loadPresetSettings();
    });
  }

  startNewPreset(): void {
    this.newPresetName = new FormControl('', {
      nonNullable: true,
      validators: control => this.validatePresetName(control),
    });
  }

  cancelNewPreset(): void {
    this.newPresetName = null;
  }

  // the new preset starts with the settings shown, gets selected, and the settings edited from now on go to it
  async createPreset(): Promise<void> {
    const control = this.newPresetName;
    if (!control || control.invalid || this.isUpdatingPresets) {
      control?.markAsTouched();
      return;
    }
    const name = control.value;
    await this.runPresetsUpdate(async () => {
      await this.flushSettingsSave();
      this.applyPresets(await this.api.createConversionPreset(name, this.selectedPreset));
      this.newPresetName = null;
      this.settingsExpanded = true;
      this.snackBar.open(`Preset "${name}" created, settings below are saved to it`, 'OK', { duration: 4000 });
    });
  }

  async deletePreset(): Promise<void> {
    const name = this.selectedPreset;
    if (!name) {
      return;
    }
    await this.runPresetsUpdate(async () => {
      await this.flushSettingsSave();
      const settings = this.presetSettingsValue();
      this.applyPresets(await this.api.deleteConversionPreset(name));
      await this.loadPresetSettings();
      this.snackBar
        .open(`Preset "${name}" removed`, 'Undo', { duration: 8000 })
        .onAction()
        .subscribe(() => this.restorePreset(name, settings));
    });
  }

  presetCommandLineArgument(preset: string): string {
    return preset.includes(' ') ? `--preset "${preset}"` : `--preset ${preset}`;
  }

  private async restorePreset(name: string, settings: Partial<ConversionConfig>): Promise<void> {
    await this.runPresetsUpdate(async () => {
      await this.flushSettingsSave();
      await this.api.createConversionPreset(name, null);
      await this.api.patchConversionConfig(settings, name);
      this.applyPresets(await this.api.getConversionPresets());
      await this.loadPresetSettings();
    });
  }

  private async runPresetsUpdate(update: () => Promise<void>): Promise<void> {
    this.isUpdatingPresets = true;
    this.cdr.markForCheck();
    try {
      await update();
    } catch (error) {
      console.error('Failed to update conversion presets:', error);
    } finally {
      this.isUpdatingPresets = false;
      this.cdr.markForCheck();
    }
  }

  private applyPresets(state: ConversionPresets): void {
    this.presets = state.presets;
    this.selectedPreset = state.selected;
  }

  private async loadPresetSettings(): Promise<void> {
    this.converterForm.patchValue(await this.api.getConversionConfig(this.selectedPreset), { emitEvent: false });
  }

  private presetSettingsValue(): ConversionConfig {
    const settings: ConversionConfig = this.converterForm.getRawValue();
    // an emptied number field would be stored as "None"
    settings.multiprocess_processes_count = Math.max(0, Math.floor(Number(settings.multiprocess_processes_count) || 0));
    return settings;
  }

  private scheduleSettingsSave(): void {
    this.pendingSettingsSave = { preset: this.selectedPreset, values: this.presetSettingsValue() };
    if (this.settingsSaveTimer) {
      clearTimeout(this.settingsSaveTimer);
    }
    this.settingsSaveTimer = setTimeout(() => this.flushSettingsSave(), SETTINGS_SAVE_DELAY_MS);
  }

  private async flushSettingsSave(): Promise<void> {
    if (this.settingsSaveTimer) {
      clearTimeout(this.settingsSaveTimer);
      this.settingsSaveTimer = null;
    }
    const save = this.pendingSettingsSave;
    this.pendingSettingsSave = null;
    if (save) {
      await this.api.patchConversionConfig(save.values, save.preset);
    }
  }

  private validatePresetName(control: AbstractControl<string>): ValidationErrors | null {
    const name: string = control.value;
    if (!name) {
      return { presetName: 'Preset name is required' };
    }
    if (name.length > PRESET_NAME_MAX_LENGTH) {
      return { presetName: `At most ${PRESET_NAME_MAX_LENGTH} characters` };
    }
    if (!PRESET_NAME_PATTERN.test(name)) {
      return {
        presetName: 'Only letters, digits, spaces, "-", "_" and ".", starting and ending with a letter or a digit',
      };
    }
    if (name.toLowerCase() === NO_PRESET_NAME.toLowerCase()) {
      return { presetName: `"${NO_PRESET_NAME}" is reserved` };
    }
    if (this.presets.some(preset => preset.toLowerCase() === name.toLowerCase())) {
      return { presetName: `Preset "${name}" already exists` };
    }
    return null;
  }
}
