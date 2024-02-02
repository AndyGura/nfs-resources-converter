import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  ComponentRef,
  Input,
  OnDestroy,
  Type,
  ViewChild,
} from '@angular/core';
import {DataBlockUIDirective} from './data-block-ui.directive';
import {FallbackBlockUiComponent} from './library/fallback.block-ui/fallback.block-ui.component';
import {GuiComponentInterface} from './gui-component.interface';
import {CompoundBlockUiComponent} from './library/compound.block-ui/compound.block-ui.component';
import {IntegerBlockUiComponent} from './library/integer.block-ui/integer.block-ui.component';
import {StringBlockUiComponent} from './library/string.block-ui/string.block-ui.component';
import {ArrayBlockUiComponent} from './library/array.block-ui/array.block-ui.component';
import {BitmapBlockUiComponent} from './eac/bitmap.block-ui/bitmap.block-ui.component';
// import { PaletteBlockUiComponent } from './eac/palette.block-ui/palette.block-ui.component';
import {BinaryBlockUiComponent} from './library/binary.block-ui/binary.block-ui.component';
// import { AngleBlockUiComponent } from './library/angle.block-ui/angle.block-ui.component';
// import { ShpiBlockUiComponent } from './eac/shpi.block-ui/shpi.block-ui.component';
// import { WwwwBlockUiComponent } from './eac/wwww.block-ui/wwww.block-ui.component';
// import { EnumBlockUiComponent } from './library/enum.block-ui/enum.block-ui.component';
// import { FlagsBlockUiComponent } from './library/flags.block-ui/flags.block-ui.component';
// import { TriMapBlockUiComponent } from './eac/tri-map.block-ui/tri-map.block-ui.component';
import {MainService} from '../../services/main.service';
import {Subject, Subscription, takeUntil} from 'rxjs';
// import { OripGeometryBlockUiComponent } from './eac/orip-geometry.block-ui/orip-geometry.block-ui.component';
import {EelDelegateService} from '../../services/eel-delegate.service';
import {DelegateBlockUiComponent} from './library/delegate.block-ui/delegate.block-ui.component';

@Component({
  selector: 'app-editor',
  templateUrl: './editor.component.html',
  styleUrls: ['./editor.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EditorComponent implements OnDestroy {
  static readonly DATA_BLOCK_COMPONENTS_MAP: { [key: string]: Type<GuiComponentInterface> } = {
    // AngleBlock: AngleBlockUiComponent,
    ArrayBlock: ArrayBlockUiComponent,
    SubByteArrayBlock: ArrayBlockUiComponent,
    // BitFlagsBlock: FlagsBlockUiComponent,
    BytesBlock: BinaryBlockUiComponent,
    CompoundBlock: CompoundBlockUiComponent,
    DataBlock: FallbackBlockUiComponent,
    DelegateBlock: DelegateBlockUiComponent,
    // EnumByteBlock: EnumBlockUiComponent,
    IntegerBlock: IntegerBlockUiComponent,
    UTF8Block: StringBlockUiComponent,
    // // NFS1 blocks
    AnyBitmapBlock: BitmapBlockUiComponent,
    // BasePalette: PaletteBlockUiComponent,
    // OripGeometry: OripGeometryBlockUiComponent,
    // ShpiBlock: ShpiBlockUiComponent,
    // TriMap: TriMapBlockUiComponent,
    // WwwwBlock: WwwwBlockUiComponent,
  };

  @ViewChild(DataBlockUIDirective, {static: true}) dataBlockUiHost!: DataBlockUIDirective;

  _component: ComponentRef<GuiComponentInterface> | null = null;
  _componentChangedSub: Subscription | null = null;

  isInReversibleSerializationState = false;

  private destroyed$: Subject<void> = new Subject<void>();
  private resourceSet$: Subject<void> = new Subject<void>();

  private _resource: Resource | null = null;
  get resource(): BlockData | ReadError | null {
    return this._resource;
  }

  private _resourceError: ResourceError | null = null;
  get resourceError(): ResourceError | null {
    return this._resourceError;
  }

  private _resourceDescription: string = '';
  @Input()
  set resourceDescription(value: string) {
    if (this._component) {
      this._component.instance.resourceDescription = value;
    }
  }

  @Input()
  public set resource(value: Resource | ResourceError | null) {
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
          this._componentChangedSub = this._component!.instance.changed.pipe(
            takeUntil(this.destroyed$),
            takeUntil(this.resourceSet$),
          ).subscribe(() => {
            this.mainService.dataBlockChange$.next([this._resource!.id, this._resource!.data]);
          });
        }
        this._component!.instance.resource = this._resource;
        this._component!.instance.resourceDescription = this._resourceDescription;
      }
    }
  }

  constructor(
    readonly mainService: MainService,
    readonly eelDelegate: EelDelegateService,
    readonly cdr: ChangeDetectorRef,
  ) {
  }

  async serializeBlockReversible() {
    const [files, isReversible] = await this.eelDelegate.serializeReversible(this.resource.name, []);
    const commonPathPart = files.reduce((commonBeginning, currentString) => {
      let j = 0;
      while (j < commonBeginning.length && j < currentString.length && commonBeginning[j] === currentString[j]) {
        j++;
      }
      return commonBeginning.substring(0, j);
    });
    await this.eelDelegate.openFileWithSystemApp(commonPathPart);
    this.isInReversibleSerializationState = isReversible;
    this.cdr.markForCheck();
  }

  async deserialize() {
    await this.mainService.deserializeResource(this.resource.name);
    this.isInReversibleSerializationState = false;
    this.cdr.markForCheck();
  }

  ngOnDestroy(): void {
    this.destroyed$.next();
    this.destroyed$.complete();
  }
}
