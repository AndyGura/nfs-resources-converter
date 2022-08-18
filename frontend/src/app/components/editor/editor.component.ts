import { ChangeDetectionStrategy, Component, ComponentRef, Input, Type, ViewChild } from '@angular/core';
import { EelDelegateService } from '../../services/eel-delegate.service';
import { DataBlockUIDirective } from './data-block-ui.directive';
import { FallbackBlockUiComponent } from './fallback.block-ui/fallback.block-ui.component';
import { GuiComponentInterface } from './gui-component.interface';
import { CompoundBlockUiComponent } from './compound.block-ui/compound.block-ui.component';
import { IntegerBlockUiComponent } from './integer.block-ui/integer.block-ui.component';
import { StringBlockUiComponent } from './string.block-ui/string.block-ui.component';
import { ArrayBlockUiComponent } from './array.block-ui/array.block-ui.component';
import { BitmapBlockUiComponent } from './bitmap.block-ui/bitmap.block-ui.component';
import { PaletteBlockUiComponent } from './palette.block-ui/palette.block-ui.component';

@Component({
  selector: 'app-editor',
  templateUrl: './editor.component.html',
  styleUrls: ['./editor.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EditorComponent {

  static readonly DATA_BLOCK_COMPONENTS_MAP: {[key: string]: Type<GuiComponentInterface>} = {
    'DataBlock': FallbackBlockUiComponent,
    'CompoundBlock': CompoundBlockUiComponent,
    'ArrayBlock': ArrayBlockUiComponent,
    'IntegerBlock': IntegerBlockUiComponent,
    'Utf8Block': StringBlockUiComponent,
    // TODO BytesField
    // TODO SubByteArrayBlock
    // NFS1 blocks
    'BasePalette': PaletteBlockUiComponent,
    'AnyBitmapBlock': BitmapBlockUiComponent,
  }

  @ViewChild(DataBlockUIDirective, { static: true }) dataBlockUiHost!: DataBlockUIDirective;

  _component: ComponentRef<GuiComponentInterface> | null = null;

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

  private _resourceData: ReadData | null = null;
  get resourceData(): ReadData | null {
    return this._resourceData;
  }
  @Input()
  public set resourceData(value: ReadData | null) {
    this._resourceData = value;
    this.dataBlockUiHost.viewContainerRef.clear();
    if (this._resourceData) {
      let component: Type<GuiComponentInterface> | undefined;
      for (const className of this._resourceData.block_class_mro.split('__')) {
          component = EditorComponent.DATA_BLOCK_COMPONENTS_MAP[className];
          if (component) {
            break;
          }
      }
      if (!component) {
        throw new Error('Cannot find GUI component for block MRO ' + this._resourceData.block_class_mro);
      }
      this._component = this.dataBlockUiHost.viewContainerRef.createComponent(component);
      this._component.instance.resourceData = this.resourceData;
      this._component.instance.name = this._name;
    }
  };

  constructor(readonly eelDelegate: EelDelegateService) {
  }

}
