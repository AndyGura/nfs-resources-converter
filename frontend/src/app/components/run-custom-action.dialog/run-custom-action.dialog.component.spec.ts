import { NO_ERRORS_SCHEMA } from '@angular/core';
import { TestBed, ComponentFixture } from '@angular/core/testing';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { RunCustomActionDialogComponent } from './run-custom-action.dialog.component';
import { CustomAction } from '../editor/types';
import { MainService } from '../../services/main.service';

describe('RunCustomActionDialogComponent', () => {
  let component: RunCustomActionDialogComponent;
  let fixture: ComponentFixture<RunCustomActionDialogComponent>;

  const action: CustomAction = {
    method: 'convert_to_8bit',
    title: 'Convert to 8bit',
    description: '',
    is_pure: false,
    args: [
      { id: 'channel', title: 'Channel', type: 'enum_string', default: 'generate embedded palette', choices: ['generate embedded palette', 'alpha'] },
      {
        id: 'palette_type',
        title: 'Palette type',
        type: 'enum_string',
        default: '32Bit color format palette',
        visible_when: { arg: 'channel', value: 'generate embedded palette' },
        choices: ['32Bit color format palette', '24Bit color format palette'],
      },
    ],
  };

  async function createComponent(formPatch?: any) {
    await TestBed.configureTestingModule({
      declarations: [RunCustomActionDialogComponent],
      providers: [
        { provide: MatDialogRef, useValue: { close: jasmine.createSpy('close') } },
        { provide: MAT_DIALOG_DATA, useValue: { action, resourceId: 'test-id', formPatch } },
        { provide: MainService, useValue: {} },
      ],
      schemas: [NO_ERRORS_SCHEMA],
    }).compileComponents();

    fixture = TestBed.createComponent(RunCustomActionDialogComponent);
    component = fixture.componentInstance;
  }

  it('starts with the gated arg visible when its default already satisfies the condition', async () => {
    await createComponent();
    expect(component.isArgVisible(action.args[1])).toBeTrue();
    expect(component.argsForm.get('palette_type')!.valid).toBeTrue();
  });

  it('hides the gated arg and drops its validators once the condition no longer holds', async () => {
    await createComponent();
    component.argsForm.get('channel')!.setValue('alpha');

    expect(component.isArgVisible(action.args[1])).toBeFalse();
    component.argsForm.get('palette_type')!.setValue('');
    expect(component.argsForm.get('palette_type')!.valid).toBeTrue();
  });

  it('re-requires the gated arg once the condition holds again', async () => {
    await createComponent();
    component.argsForm.get('channel')!.setValue('alpha');
    component.argsForm.get('channel')!.setValue('generate embedded palette');

    expect(component.isArgVisible(action.args[1])).toBeTrue();
    component.argsForm.get('palette_type')!.setValue('');
    expect(component.argsForm.get('palette_type')!.valid).toBeFalse();
  });

  it('is always visible for an arg without visible_when', async () => {
    await createComponent();
    expect(component.isArgVisible(action.args[0])).toBeTrue();
  });

  it('renders without error', async () => {
    await createComponent();
    expect(() => fixture.detectChanges()).not.toThrow();
  });
});
