import { NO_ERRORS_SCHEMA } from '@angular/core';
import { TestBed, ComponentFixture } from '@angular/core/testing';
import { BehaviorSubject } from 'rxjs';
import { ArrayBlockUiComponent } from './array.block-ui.component';
import { MainService } from '../../../../services/main.service';
import { ChangesService } from '../../../../services/changes.service';
import { NavigationService } from '../../../../services/navigation.service';
import { BlockSchema } from '../../types';

describe('ArrayBlockUiComponent', () => {
  let component: ArrayBlockUiComponent;
  let fixture: ComponentFixture<ArrayBlockUiComponent>;
  let mockMainService: any;
  let mockChangesService: any;
  let mockNavigationService: any;

  beforeEach(async () => {
    mockMainService = {
      focusedResourceId$: new BehaviorSubject<string | null>(null),
      getNewItemData: jasmine.createSpy('getNewItemData').and.returnValue(Promise.resolve({ val: 42 })),
    };

    mockChangesService = {
      subscribeComponent: jasmine.createSpy('subscribeComponent'),
      unsubscribeComponent: jasmine.createSpy('unsubscribeComponent'),
      appendChanges: jasmine.createSpy('appendChanges').and.returnValue(Promise.resolve()),
    };

    mockNavigationService = {
      navigationPath$: new BehaviorSubject<string[]>([]),
      resourceToRender$: new BehaviorSubject<any | null>(null),
      navigateToId: jasmine.createSpy('navigateToId'),
      navigateBack: jasmine.createSpy('navigateBack'),
    };

    await TestBed.configureTestingModule({
      declarations: [ArrayBlockUiComponent],
      providers: [
        { provide: MainService, useValue: mockMainService },
        { provide: ChangesService, useValue: mockChangesService },
        { provide: NavigationService, useValue: mockNavigationService },
      ],
      schemas: [NO_ERRORS_SCHEMA],
    }).compileComponents();

    fixture = TestBed.createComponent(ArrayBlockUiComponent);
    component = fixture.componentInstance;
    component.resourceId = 'test-id';
  });

  it('should create the component', () => {
    expect(component).toBeTruthy();
  });

  describe('Table Simplicity Indicator', () => {
    it('should render as table for Case 1: Rows are primitives', () => {
      const primitiveSchema: BlockSchema = {
        block_class_mro: 'ArrayBlock__',
        child_schema: {
          block_class_mro: 'IntegerBlock__',
          length: 1,
        },
      };

      component.resourceSchema = primitiveSchema;
      component.resourceData = [1, 2, 3, 4];

      expect(component.isTable).toBeTrue();
      expect(component.tableColumns).toEqual(['index', 'data']);
      expect(component.arrayTableColumns?.length).toBe(1);
      expect(component.arrayTableColumns?.[0].key).toBe('data');
    });

    it('should render as table for Case 2: Rows are ArrayBlocks of primitives (2D array)', () => {
      const array2DPrimitiveSchema: BlockSchema = {
        block_class_mro: 'ArrayBlock__',
        child_schema: {
          block_class_mro: 'ArrayBlock__',
          length: 3,
          child_schema: {
            block_class_mro: 'IntegerBlock__',
            length: 1,
          },
        },
      };

      component.resourceSchema = array2DPrimitiveSchema;
      component.resourceData = [
        [1, 2, 3],
        [4, 5, 6],
      ];

      expect(component.isTable).toBeTrue();
      expect(component.tableColumns).toEqual(['index', '0', '1', '2']);
      expect(component.arrayTableColumns?.length).toBe(3);
      expect(component.arrayTableColumns?.[0].key).toBe('0');
    });

    it('should render as table for Case 2: Rows are ArrayBlocks of compounds (array_2d_comp)', () => {
      const array2DCompSchema: BlockSchema = {
        block_class_mro: 'ArrayBlock__',
        child_schema: {
          block_class_mro: 'ArrayBlock__',
          length: 2,
          child_schema: {
            block_class_mro: 'CompoundBlock__',
            fields: [
              {
                name: 'x',
                schema: {
                  block_class_mro: 'IntegerBlock__',
                },
              },
              {
                name: 'y',
                schema: {
                  block_class_mro: 'IntegerBlock__',
                },
              },
            ],
          },
        },
      };

      component.resourceSchema = array2DCompSchema;
      component.resourceData = [
        [
          { x: 1, y: 2 },
          { x: 3, y: 4 },
        ],
        [
          { x: 5, y: 6 },
          { x: 7, y: 8 },
        ],
      ];

      expect(component.isTable).toBeTrue();
      expect(component.tableColumns).toEqual(['index', '0', '1']);
      expect(component.arrayTableColumns?.length).toBe(2);
      expect(component.arrayTableColumns?.[0].subFields?.length).toBe(2);
      expect(component.arrayTableColumns?.[0].subFields?.[0].key).toBe('x');
    });

    it('should render as table for Case 3: Rows are CompoundBlocks containing array fields (array_comp_array)', () => {
      const arrayCompArraySchema: BlockSchema = {
        block_class_mro: 'ArrayBlock__',
        child_schema: {
          block_class_mro: 'CompoundBlock__',
          fields: [
            {
              name: 'vector',
              schema: {
                block_class_mro: 'ArrayBlock__',
                length: 3,
                child_schema: {
                  block_class_mro: 'IntegerBlock__',
                },
              },
            },
            {
              name: 'extra',
              schema: {
                block_class_mro: 'IntegerBlock__',
              },
            },
          ],
        },
      };

      component.resourceSchema = arrayCompArraySchema;
      component.resourceData = [
        { vector: [1, 2, 3], extra: 42 },
        { vector: [4, 5, 6], extra: 84 },
      ];

      expect(component.isTable).toBeTrue();
      expect(component.tableColumns).toEqual(['index', 'vector', 'extra']);
      expect(component.arrayTableColumns?.length).toBe(2);
      expect(component.arrayTableColumns?.[0].key).toBe('vector');
      expect(component.arrayTableColumns?.[0].subFields?.length).toBe(3);
      expect(component.arrayTableColumns?.[0].subFields?.[0].key).toBe('0');
      expect(component.arrayTableColumns?.[1].key).toBe('extra');
    });

    it('should NOT render as table if inner array length exceeds 32', () => {
      const arrayTooLongSchema: BlockSchema = {
        block_class_mro: 'ArrayBlock__',
        child_schema: {
          block_class_mro: 'ArrayBlock__',
          length: 33,
          child_schema: {
            block_class_mro: 'IntegerBlock__',
          },
        },
      };

      component.resourceSchema = arrayTooLongSchema;
      component.resourceData = [new Array(33).fill(1)];

      expect(component.isTable).toBeFalse();
    });

    it('should NOT render as table if compound child is not simple (deep nesting)', () => {
      const complexSchema: BlockSchema = {
        block_class_mro: 'ArrayBlock__',
        child_schema: {
          block_class_mro: 'CompoundBlock__',
          fields: [
            {
              name: 'complexField',
              schema: {
                block_class_mro: 'CompoundBlock__',
                fields: [
                  {
                    name: 'deeplyNested',
                    schema: {
                      block_class_mro: 'CompoundBlock__', // nested compound
                    },
                  },
                ],
              },
            },
          ],
        },
      };

      component.resourceSchema = complexSchema;
      component.resourceData = [{ complexField: { deeplyNested: {} } }];

      expect(component.isTable).toBeFalse();
    });
  });

  describe('Item Manipulation and Actions', () => {
    beforeEach(() => {
      component.resourceId = 'test-id';
      component.resourceSchema = {
        block_class_mro: 'ArrayBlock__',
        child_schema: {
          block_class_mro: 'IntegerBlock__',
          length: 1,
        },
      };
      component.resourceData = [10, 20, 30];
    });

    it('should add item using MainService and emit change', async () => {
      await component.addItem();
      expect(mockMainService.getNewItemData).toHaveBeenCalledWith('test-id');
      expect(mockChangesService.appendChanges).toHaveBeenCalled();
      const lastCallArg = mockChangesService.appendChanges.calls.mostRecent().args[0];
      expect(lastCallArg.op).toBe('array_insert');
      expect(lastCallArg.index).toBe(3);
      expect(lastCallArg.value).toEqual({ val: 42 });
    });

    it('should remove item and emit change', () => {
      component.removeItem(1);
      expect(mockChangesService.appendChanges).toHaveBeenCalled();
      const lastCallArg = mockChangesService.appendChanges.calls.mostRecent().args[0];
      expect(lastCallArg.op).toBe('array_remove');
      expect(lastCallArg.index).toBe(1);
      expect(lastCallArg.oldValue).toBe(20);
    });

    it('should move item up and emit swap change', () => {
      component.moveItemUp(2);
      expect(mockChangesService.appendChanges).toHaveBeenCalled();
      const lastCallArg = mockChangesService.appendChanges.calls.mostRecent().args[0];
      expect(lastCallArg.op).toBe('array_swap');
      expect(lastCallArg.indexA).toBe(2);
      expect(lastCallArg.indexB).toBe(1);
    });

    it('should move item down and emit swap change', () => {
      component.moveItemDown(0);
      expect(mockChangesService.appendChanges).toHaveBeenCalled();
      const lastCallArg = mockChangesService.appendChanges.calls.mostRecent().args[0];
      expect(lastCallArg.op).toBe('array_swap');
      expect(lastCallArg.indexA).toBe(0);
      expect(lastCallArg.indexB).toBe(1);
    });
  });
});
