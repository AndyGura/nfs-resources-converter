import { ChangeDetectionStrategy, Component, ComponentRef, Input, OnDestroy, Type, ViewChild } from '@angular/core';
import { DataBlockUIDirective } from './data-block-ui.directive';
import { FallbackBlockUiComponent } from './library/fallback.block-ui/fallback.block-ui.component';
import { GuiComponentInterface } from './gui-component.interface';
import { CompoundBlockUiComponent } from './library/compound.block-ui/compound.block-ui.component';
import { NumberBlockUiComponent } from './library/number.block-ui/number.block-ui.component';
import { StringBlockUiComponent } from './library/string.block-ui/string.block-ui.component';
import { ArrayBlockUiComponent } from './library/array.block-ui/array.block-ui.component';
import { BitmapBlockUiComponent } from './eac/bitmap.block-ui/bitmap.block-ui.component';
import { PaletteBlockUiComponent } from './eac/palette.block-ui/palette.block-ui.component';
import { BinaryBlockUiComponent } from './library/binary.block-ui/binary.block-ui.component';
import { AngleBlockUiComponent } from './eac/angle.block-ui/angle.block-ui.component';
import { WwwwBlockUiComponent } from './eac/wwww.block-ui/wwww.block-ui.component';
import { EnumBlockUiComponent } from './library/enum.block-ui/enum.block-ui.component';
import { FlagsBlockUiComponent } from './library/flags.block-ui/flags.block-ui.component';
import { TriMapBlockUiComponent } from './eac/tri-map.block-ui/tri-map.block-ui.component';
import { MainService } from '../../services/main.service';
import { Subject, Subscription, takeUntil } from 'rxjs';
import { OripGeometryBlockUiComponent } from './eac/orip-geometry.block-ui/orip-geometry.block-ui.component';
import { DelegateBlockUiComponent } from './library/delegate.block-ui/delegate.block-ui.component';
import { joinId } from '../../utils/join-id';
import isObject from 'lodash/isObject';
import { FenceTypeBlockUiComponent } from './eac/fence-type.block-ui/fence-type.block-ui.component';
import { SoundbankBlockUiComponent } from './eac/soundbank.block-ui/soundbank.block-ui.component';
import { EacsAudioBlockUiComponent } from './eac/eacs-audio.block-ui/eacs-audio.block-ui.component';
import { GeoGeometryBlockUiComponent } from './eac/geo-geometry.block-ui/geo-geometry.block-ui.component';
import { BaseArchiveBlockUiComponent } from './eac/base-archive.block-ui/base-archive.block-ui.component';
import { TrkMapBlockUiComponent } from './eac/trk-map.block-ui/trk-map.block-ui.component';
import { NgxDeepEqualsPureService } from 'ngx-deep-equals-pure';
import { SkipBlockUiComponent } from './library/skip.block-ui/skip.block-ui.component';
import { FrdMapBlockUiComponent } from './eac/frd-map.block-ui/frd-map.block-ui.component';

@Component({
  selector: 'app-editor',
  templateUrl: './editor.component.html',
  styleUrls: ['./editor.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EditorComponent implements OnDestroy {
  static readonly DATA_BLOCK_COMPONENTS_MAP: { [key: string]: Type<GuiComponentInterface> } = {
    ArrayBlock: ArrayBlockUiComponent,
    SubByteArrayBlock: ArrayBlockUiComponent,

    BitFlagsBlock: FlagsBlockUiComponent,
    BytesBlock: BinaryBlockUiComponent,
    CompoundBlock: CompoundBlockUiComponent,
    DataBlock: FallbackBlockUiComponent,
    DelegateBlock: DelegateBlockUiComponent,
    EnumByteBlock: EnumBlockUiComponent,

    IntegerBlock: NumberBlockUiComponent,
    DecimalBlock: NumberBlockUiComponent,

    UTF8Block: StringBlockUiComponent,
    NullTerminatedUTF8Block: StringBlockUiComponent,

    SkipBlock: SkipBlockUiComponent,
    // NFS1 blocks
    AngleBlock: AngleBlockUiComponent,
    AnyBitmapBlock: BitmapBlockUiComponent,
    BasePalette: PaletteBlockUiComponent,
    OripGeometry: OripGeometryBlockUiComponent,
    BaseArchiveBlock: BaseArchiveBlockUiComponent,
    TriMap: TriMapBlockUiComponent,
    WwwwBlock: WwwwBlockUiComponent,
    FenceType: FenceTypeBlockUiComponent,
    SoundBank: SoundbankBlockUiComponent,
    EacsAudioFile: EacsAudioBlockUiComponent,
    // NFS2 blocks
    GeoGeometry: GeoGeometryBlockUiComponent,
    TrkMap: TrkMapBlockUiComponent,
    // NFS3 blocks
    FrdMap: FrdMapBlockUiComponent,
  };

  @ViewChild(DataBlockUIDirective, { static: true }) dataBlockUiHost!: DataBlockUIDirective;

  _component: ComponentRef<GuiComponentInterface> | null = null;
  _componentChangedSub: Subscription | null = null;

  private destroyed$: Subject<void> = new Subject<void>();
  private resourceSet$: Subject<void> = new Subject<void>();

  private _resource: Resource | null = null;
  get resource(): Resource | null {
    return this._resource;
  }

  private _resourceError: ResourceError | null = null;
  get resourceError(): ResourceError | null {
    return this._resourceError;
  }

  private _resourceDescription: string = '';
  @Input()
  set resourceDescription(value: string) {
    this._resourceDescription = value;
    if (this._component) {
      this._component.instance.resourceDescription = value;
    }
  }

  private _hideBlockActions: boolean = false;
  @Input()
  set hideBlockActions(value: boolean) {
    this._hideBlockActions = value;
    if (this._component) {
      this._component.instance.hideBlockActions = value;
    }
  }

  private _disabled: boolean = false;
  @Input()
  set disabled(value: boolean) {
    this._disabled = value;
    if (this._component) {
      this._component.instance.disabled = value;
    }
  }

  resourceEqual(resA: Resource | ResourceError | null, resB: Resource | ResourceError | null): boolean {
    if (!resA || !resB) {
      return !resA === !resB;
    }
    return resA.id === resB.id && this.deep.deepEquals(resA.data, resB.data);
  }

  @Input()
  public set resource(value: Resource | ResourceError | null) {
    if (this.resourceEqual(value, this._resourceError || this._resource)) {
      return;
    }
    this.resourceSet$.next();
    // TODO reusing components does not work for some reason. At least when child is compound block with the same schema
    let reuseComponent = false; //!!this._component && value && this._resource && value.schema.block_class_mro === this._resource.schema.block_class_mro;
    if (!value) {
      this._resource = null;
      this._resourceError = null;
    } else if (value.data?.error_class) {
      this._resourceError = value;
      this._resource = null;
    } else {
      this._resource = value;
      this._resourceError = null;
    }
    this.dataBlockUiHost.viewContainerRef.clear();
    if (this._resource) {
      if (this._resource.schema.block_class_mro) {
        if (!reuseComponent) {
          let component: Type<GuiComponentInterface> | undefined;
          for (const className of this._resource.schema.block_class_mro.split('__')) {
            component = EditorComponent.DATA_BLOCK_COMPONENTS_MAP[className];
            if (component) {
              break;
            }
          }
          if (!component) {
            throw new Error('Cannot find GUI component for block MRO ' + this._resource.schema.block_class_mro);
          }
          if (this._component && this._componentChangedSub) {
            this._componentChangedSub.unsubscribe();
          }
          this._component = this.dataBlockUiHost.viewContainerRef.createComponent(component);
          this._componentChangedSub = this._component.instance.changed
            .pipe(takeUntil(this.destroyed$), takeUntil(this.resourceSet$))
            .subscribe(() => {
              const id = this._resource!.id;
              const data = this._resource!.data;
              if (data instanceof Array) {
                if (this._resource!.schema.block_class_mro.startsWith('BytesBlock')) {
                  // for bytes block we save whole array
                  this.mainService.dataBlockChange$.next([id, data]);
                } else {
                  for (let i = 0; i < data.length; i++) {
                    this.mainService.dataBlockChange$.next([joinId(id, i), data[i]]);
                  }
                }
              } else if (isObject(data)) {
                for (const key in data) {
                  this.mainService.dataBlockChange$.next([joinId(id, key), (data as any)[key]]);
                }
              } else {
                this.mainService.dataBlockChange$.next([id, data]);
              }
            });
        }
        this._component!.instance.resource = this._resource;
        this._component!.instance.resourceDescription = this._resourceDescription;
        this._component!.instance.hideBlockActions = this._hideBlockActions;
        this._component!.instance.disabled = this._disabled;
      }
    }
  }

  constructor(readonly mainService: MainService, private readonly deep: NgxDeepEqualsPureService) {}

  ngOnDestroy(): void {
    this.destroyed$.next();
    this.destroyed$.complete();
  }
}
