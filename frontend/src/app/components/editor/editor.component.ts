import { ChangeDetectionStrategy, Component, ComponentRef, Input, OnDestroy, Type, ViewChild } from '@angular/core';
import { DataBlockUIDirective } from './data-block-ui.directive';
import { FallbackBlockUiComponent } from './library/fallback.block-ui/fallback.block-ui.component';
import { GuiComponentInterfaceNew } from './gui-component.interface';
import { MainService } from '../../services/main.service';
import { Subject, Subscription, takeUntil } from 'rxjs';
import { joinId } from '../../utils/join-id';
import isObject from 'lodash/isObject';
import { Resource, ResourceError } from './types';

@Component({
  selector: 'app-editor',
  templateUrl: './editor.component.html',
  styleUrls: ['./editor.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EditorComponent implements OnDestroy {
  static readonly DATA_BLOCK_COMPONENTS_MAP: { [key: string]: Type<GuiComponentInterfaceNew> } = {
    // General
    DataBlock: FallbackBlockUiComponent,

    // ArrayBlock: ArrayBlockUiComponent,
    // SubByteArrayBlock: ArrayBlockUiComponent,
    //
    // SubByteCompoundBlock: SubByteCompoundBlockUiComponent,
    // BytesBlock: BinaryBlockUiComponent,
    // CompoundBlock: CompoundBlockUiComponent,
    // DelegateBlock: DelegateBlockUiComponent,
    // EnumByteBlock: EnumBlockUiComponent,
    //
    // IntegerBlock: NumberBlockUiComponent,
    // DecimalBlock: NumberBlockUiComponent,
    //
    // UTF8Block: StringBlockUiComponent,
    // NullTerminatedUTF8Block: StringBlockUiComponent,
    //
    // SkipBlock: SkipBlockUiComponent,
    // // NFS1 blocks
    // AngleBlock: AngleBlockUiComponent,
    // EacImage: ImageBlockUiComponent,
    // EacPalette: PaletteBlockUiComponent,
    // OripGeometry: OripGeometryBlockUiComponent,
    // BaseArchiveBlock: BaseArchiveBlockUiComponent,
    // TriMap: TriMapBlockUiComponent,
    // WwwwBlock: WwwwBlockUiComponent,
    // SoundBank: SoundbankBlockUiComponent,
    // EacsAudioFile: EacsAudioBlockUiComponent,
    // // NFS2 blocks
    // GeoGeometry: GeoGeometryBlockUiComponent,
    // TrkMap: TrkMapBlockUiComponent,
    // // NFS3 blocks
    // FrdMap: FrdMapBlockUiComponent,
    // // NFS5 blocks
    // CrpGeometry: CrpGeometryBlockUiComponent,
  };

  @ViewChild(DataBlockUIDirective, { static: true }) dataBlockUiHost!: DataBlockUIDirective;

  _component: ComponentRef<GuiComponentInterfaceNew> | null = null;
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

  private _hideName: boolean = false;
  @Input()
  set hideName(value: boolean) {
    this._hideName = value;
    if (this._component) {
      this._component.instance.hideName = value;
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

  // resourceEqual(resA: Resource | ResourceError | null, resB: Resource | ResourceError | null): boolean {
  //   if (!resA || !resB) {
  //     return !resA === !resB;
  //   }
  //   if (resA.id !== resB.id) {
  //     return false;
  //   }
  //   if (resA === resB || resA.data === resB.data) {
  //     return true;
  //   }
  //   return this.deep.deepEquals(resA.data, resB.data);
  // }

  @Input()
  public set resource(value: Resource | ResourceError | null) {
    this.resourceSet$.next();
    let reuseComponent =
      !!this._component &&
      value &&
      this._resource &&
      value.schema.block_class_mro === this._resource.schema.block_class_mro;
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
    if (!reuseComponent) {
      this.dataBlockUiHost.viewContainerRef.clear();
    }
    if (this._resource) {
      if (this._resource.schema.block_class_mro) {
        if (!reuseComponent) {
          let component: Type<GuiComponentInterfaceNew> | undefined;
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
                if (this._resource!.schema.block_class_mro.includes('BytesBlock')) {
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
        this._component!.instance.resourceId = this._resource.id;
        this._component!.instance.resourceName = this._resource.name;
        this._component!.instance.resourceSchema = this._resource.schema;
        this._component!.instance.resourceData = this._resource.data;
        this._component!.instance.resourceDescription = this._resourceDescription;
        this._component!.instance.hideName = this._hideName;
        this._component!.instance.hideBlockActions = this._hideBlockActions;
        this._component!.instance.disabled = this._disabled;
        if (reuseComponent) {
          this._component!.changeDetectorRef.markForCheck();
        }
      }
    }
  }

  constructor(readonly mainService: MainService) {}

  ngOnDestroy(): void {
    this.destroyed$.next();
    this.destroyed$.complete();
  }
}
