import { NO_ERRORS_SCHEMA } from '@angular/core';
import { TestBed, ComponentFixture } from '@angular/core/testing';
import { TrailingOptionalBlockUiComponent } from './trailing-optional.block-ui.component';
import { MainService } from '../../../../services/main.service';
import { ChangesService } from '../../../../services/changes.service';

describe('TrailingOptionalBlockUiComponent', () => {
  let component: TrailingOptionalBlockUiComponent;
  let fixture: ComponentFixture<TrailingOptionalBlockUiComponent>;
  let mockMainService: any;
  let mockChangesService: any;

  beforeEach(async () => {
    mockMainService = {
      getTrailingOptionalFieldData: jasmine
        .createSpy('getTrailingOptionalFieldData')
        .and.returnValue(Promise.resolve(0)),
    };

    mockChangesService = {
      subscribeComponent: jasmine.createSpy('subscribeComponent'),
      unsubscribeComponent: jasmine.createSpy('unsubscribeComponent'),
      appendChanges: jasmine.createSpy('appendChanges').and.returnValue(Promise.resolve()),
    };

    await TestBed.configureTestingModule({
      declarations: [TrailingOptionalBlockUiComponent],
      providers: [
        { provide: MainService, useValue: mockMainService },
        { provide: ChangesService, useValue: mockChangesService },
      ],
      schemas: [NO_ERRORS_SCHEMA],
    }).compileComponents();

    fixture = TestBed.createComponent(TrailingOptionalBlockUiComponent);
    component = fixture.componentInstance;
    component.resourceId = 'test-id';
    component.resourceSchema = {
      block_class_mro: 'TrailingOptionalBlock__OptionalBlock__DataBlock',
      is_optional: true,
      criteria: 'at least 1 byte remaining',
      child_schema: { block_class_mro: 'IntegerBlock__DataBlock' },
    };
  });

  it('should create the component', () => {
    expect(component).toBeTruthy();
  });

  it('reports absent when data is null', () => {
    component.resourceData = null;
    expect(component.isPresent).toBeFalse();
  });

  it('reports present when data is not null', () => {
    component.resourceData = 0;
    expect(component.isPresent).toBeTrue();
  });

  it('fetches new child data from the API and emits a set change when turned on', async () => {
    component.resourceData = null;
    await component.setPresent(true);

    expect(mockMainService.getTrailingOptionalFieldData).toHaveBeenCalledWith('test-id');
    expect(mockChangesService.appendChanges).toHaveBeenCalled();
    const change = mockChangesService.appendChanges.calls.mostRecent().args[0];
    expect(change.op).toBe('set');
    expect(change.id).toBe('test-id');
    expect(change.oldValue).toBeNull();
    expect(change.newValue).toBe(0);
  });

  it('emits a null set change when turned off, without calling the API', async () => {
    component.resourceData = 42;
    await component.setPresent(false);

    expect(mockMainService.getTrailingOptionalFieldData).not.toHaveBeenCalled();
    const change = mockChangesService.appendChanges.calls.mostRecent().args[0];
    expect(change.op).toBe('set');
    expect(change.oldValue).toBe(42);
    expect(change.newValue).toBeNull();
  });

  it('renders without error when absent', () => {
    component.resourceData = null;
    expect(() => fixture.detectChanges()).not.toThrow();
  });

  it('renders without error, nesting the child editor, when present', () => {
    component.resourceData = 5;
    expect(() => fixture.detectChanges()).not.toThrow();
    expect(fixture.nativeElement.querySelector('app-editor')).toBeTruthy();
  });

  it('does nothing when asked to set its already-current presence state', async () => {
    component.resourceData = 42;
    await component.setPresent(true);
    expect(mockChangesService.appendChanges).not.toHaveBeenCalled();

    component.resourceData = null;
    await component.setPresent(false);
    expect(mockChangesService.appendChanges).not.toHaveBeenCalled();
  });
});
