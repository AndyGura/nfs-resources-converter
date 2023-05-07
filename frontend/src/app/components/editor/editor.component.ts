import { ChangeDetectionStrategy, Component, ComponentRef, Input, OnDestroy, Type, ViewChild } from '@angular/core';
import { DataBlockUIDirective } from './data-block-ui.directive';
import { FallbackBlockUiComponent } from './library/fallback.block-ui/fallback.block-ui.component';
import { GuiComponentInterface } from './gui-component.interface';
import { CompoundBlockUiComponent } from './library/compound.block-ui/compound.block-ui.component';
import { IntegerBlockUiComponent } from './library/integer.block-ui/integer.block-ui.component';
import { StringBlockUiComponent } from './library/string.block-ui/string.block-ui.component';
import { ArrayBlockUiComponent } from './library/array.block-ui/array.block-ui.component';
import { BitmapBlockUiComponent } from './eac/bitmap.block-ui/bitmap.block-ui.component';
import { PaletteBlockUiComponent } from './eac/palette.block-ui/palette.block-ui.component';
import { BinaryBlockUiComponent } from './library/binary.block-ui/binary.block-ui.component';
import { AngleBlockUiComponent } from './library/angle.block-ui/angle.block-ui.component';
import { ShpiBlockUiComponent } from './eac/shpi.block-ui/shpi.block-ui.component';
import { WwwwBlockUiComponent } from './eac/wwww.block-ui/wwww.block-ui.component';
import { EnumBlockUiComponent } from './library/enum.block-ui/enum.block-ui.component';
import { FlagsBlockUiComponent } from './library/flags.block-ui/flags.block-ui.component';
import { TriMapBlockUiComponent } from './eac/tri-map.block-ui/tri-map.block-ui.component';
import { MainService } from '../../services/main.service';
import { Subject, Subscription, takeUntil } from 'rxjs';
import { OripGeometryBlockUiComponent } from './eac/orip-geometry.block-ui/orip-geometry.block-ui.component'

@Component({
  selector: 'app-editor',
  templateUrl: './editor.component.html',
  styleUrls: ['./editor.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EditorComponent implements OnDestroy {

  static readonly DATA_BLOCK_COMPONENTS_MAP: { [key: string]: Type<GuiComponentInterface> } = {
    'DataBlock': FallbackBlockUiComponent,
    'CompoundBlock': CompoundBlockUiComponent,
    'ArrayBlock': ArrayBlockUiComponent,
    'IntegerBlock': IntegerBlockUiComponent,
    'AngleBlock': AngleBlockUiComponent,
    'Utf8Block': StringBlockUiComponent,
    'BytesField': BinaryBlockUiComponent,
    'EnumByteBlock': EnumBlockUiComponent,
    'BitFlagsBlock': FlagsBlockUiComponent,
    // TODO SubByteArrayBlock
    // NFS1 blocks
    'BasePalette': PaletteBlockUiComponent,
    'AnyBitmapBlock': BitmapBlockUiComponent,
    'TriMap': TriMapBlockUiComponent,
    'ShpiBlock': ShpiBlockUiComponent,
    'WwwwBlock': WwwwBlockUiComponent,
    'OripGeometry': OripGeometryBlockUiComponent,
  }

  @ViewChild(DataBlockUIDirective, { static: true }) dataBlockUiHost!: DataBlockUIDirective;

  _component: ComponentRef<GuiComponentInterface> | null = null;
  _componentChangedSub: Subscription | null = null;

  private destroyed$: Subject<void> = new Subject<void>();

  private _name: string = '';
  get name(): string {
    return this._name;
  }

  @Input()
  public set name(value: string) {
    this._name = value;
    if (this._component?.instance) {
      this._component.instance.name = value;
    }
  };

  private _resourceData: ReadData | ReadError | null = null;
  get resourceData(): ReadData | ReadError | null {
    return this._resourceData;
  }

  get error(): ReadError | null {
    if ((this._resourceData as any)?.error_class) {
      return this._resourceData as ReadError;
    }
    return null;
  }

  @Input()
  public set resourceData(value: ReadData | ReadError | null) {
    this._resourceData = value;
    this.dataBlockUiHost.viewContainerRef.clear();
    if (this._resourceData) {
      if ((this._resourceData as any).block_class_mro) {
        const readData = this._resourceData as ReadData;
        let component: Type<GuiComponentInterface> | undefined;
        for (const className of readData.block_class_mro.split('__')) {
          component = EditorComponent.DATA_BLOCK_COMPONENTS_MAP[className];
          if (component) {
            break;
          }
        }
        if (!component) {
          throw new Error('Cannot find GUI component for block MRO ' + readData.block_class_mro);
        }
        if (this._component && this._componentChangedSub) {
          this._componentChangedSub.unsubscribe();
        }
        this._component = this.dataBlockUiHost.viewContainerRef.createComponent(component);
        this._component.instance.resourceData = readData;
        this._component.instance.name = this._name;
        this._componentChangedSub = this._component.instance.changed
          .pipe(takeUntil(this.destroyed$))
          .subscribe(() => {
            this.mainService.dataBlockChange$.next([readData.block_id, readData.value]);
          });
      }
    }
  };

  constructor(readonly mainService: MainService) {
  }

  ngOnDestroy(): void {
    this.destroyed$.next();
    this.destroyed$.complete();
  }

}
