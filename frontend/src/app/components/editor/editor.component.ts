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
import { DataBlockUIDirective } from './data-block-ui.directive';
import { GuiComponent } from './gui.component';
import { MainService } from '../../services/main.service';
import { Subject, Subscription } from 'rxjs';
import { BlockData, BlockSchema, Resource, ResourceError, schemaEquals } from './types';
import { CompoundBlockUiComponent } from './library/compound.block-ui/compound.block-ui.component';
import { NumberBlockUiComponent } from './library/number.block-ui/number.block-ui.component';
import { StringBlockUiComponent } from './library/string.block-ui/string.block-ui.component';
import { ArrayBlockUiComponent } from './library/array.block-ui/array.block-ui.component';
import { DelegateBlockUiComponent } from './library/delegate.block-ui/delegate.block-ui.component';
import { EnumBlockUiComponent } from './library/enum.block-ui/enum.block-ui.component';
import { BinaryBlockUiComponent } from './library/binary.block-ui/binary.block-ui.component';
import { SubByteCompoundBlockUiComponent } from './library/sub-byte-compound.block-ui/sub-byte-compound.block-ui.component';
import { AngleBlockUiComponent } from './eac/angle.block-ui/angle.block-ui.component';
import { ChangesService } from '../../services/changes.service';
import { BaseArchiveBlockUiComponent } from './eac/base-archive.block-ui/base-archive.block-ui.component';
import { ImageBlockUiComponent } from './eac/image.block-ui/image.block-ui.component';
import { PaletteBlockUiComponent } from './eac/palette.block-ui/palette.block-ui.component';
import { OripGeometryBlockUiComponent } from './eac/orip-geometry.block-ui/orip-geometry.block-ui.component';
import { EacsAudioBlockUiComponent } from './eac/eacs-audio.block-ui/eacs-audio.block-ui.component';
import { SoundbankBlockUiComponent } from './eac/soundbank.block-ui/soundbank.block-ui.component';
import { TriMapBlockUiComponent } from './eac/tri-map.block-ui/tri-map.block-ui.component';
import { GeoGeometryBlockUiComponent } from './eac/geo-geometry.block-ui/geo-geometry.block-ui.component';
import { TrkMapBlockUiComponent } from './eac/trk-map.block-ui/trk-map.block-ui.component';
import { FrdMapBlockUiComponent } from './eac/frd-map.block-ui/frd-map.block-ui.component';
import { CrpGeometryBlockUiComponent } from './eac/crp-geometry.block-ui/crp-geometry.block-ui.component';
import { FontBlockUiComponent } from './eac/font.block-ui/font.block-ui.component';
import { ArchiveBlockUiComponent } from './library/archive.block-ui/archive.block-ui.component';

@Component({
  selector: 'app-editor',
  templateUrl: './editor.component.html',
  styleUrls: ['./editor.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  standalone: false,
})
export class EditorComponent implements OnDestroy {
  static readonly DATA_BLOCK_COMPONENTS_MAP: { [key: string]: Type<GuiComponent> } = {
    // basic primitives
    IntegerBlock: NumberBlockUiComponent,
    DecimalBlock: NumberBlockUiComponent,
    UTF8Block: StringBlockUiComponent,
    NullTerminatedUTF8Block: StringBlockUiComponent,
    EnumByteBlock: EnumBlockUiComponent,
    BytesBlock: BinaryBlockUiComponent,

    // basic containers
    ArchiveBlock: ArchiveBlockUiComponent,
    ArrayBlock: ArrayBlockUiComponent,
    SubByteArrayBlock: ArrayBlockUiComponent,
    CompoundBlock: CompoundBlockUiComponent,
    SubByteCompoundBlock: SubByteCompoundBlockUiComponent,
    DelegateBlock: DelegateBlockUiComponent,

    // misc
    AngleBlock: AngleBlockUiComponent,

    // Common classic Need For Speed blocks
    BaseArchiveBlock: BaseArchiveBlockUiComponent,
    EacImage: ImageBlockUiComponent,
    EacPalette: PaletteBlockUiComponent,
    FfnFont: FontBlockUiComponent,

    // TNFS-specific blocks
    OripGeometry: OripGeometryBlockUiComponent,
    EacsAudioFile: EacsAudioBlockUiComponent,
    SoundBank: SoundbankBlockUiComponent,
    TriMap: TriMapBlockUiComponent,

    // NFS2-specific blocks
    GeoGeometry: GeoGeometryBlockUiComponent,
    TrkMap: TrkMapBlockUiComponent,

    // NFS3-specific blocks
    FrdMap: FrdMapBlockUiComponent,

    // NFS5-specific blocks
    CrpGeometry: CrpGeometryBlockUiComponent,
  };

  _resourceId?: string;
  _resourceName?: string;
  _resourceSchema?: BlockSchema;
  _resourceData?: BlockData;

  @Input()
  public set resourceOrError(value: Resource | ResourceError | null) {
    this._resourceId = value?.id;
    this._resourceName = value?.name;
    this.resourceError = null;
    if (value?.data?.error_class !== undefined) {
      this.resourceError = { class: value?.data?.error_class, message: value?.data?.error_text };
      this._resourceSchema = undefined;
      this._resourceData = undefined;
      return;
    }

    this._resourceData = value?.data;
    if (this._resourceSchema !== value?.schema) {
      let reuseComponent =
        !!this._component &&
        value &&
        this._resourceSchema &&
        value.schema?.block_class_mro === this._resourceSchema.block_class_mro;
      this._resourceSchema = value?.schema;

      if (!reuseComponent) {
        this.dataBlockUiHost.viewContainerRef.clear();
      }
      if (this._resourceSchema?.block_class_mro) {
        if (!reuseComponent) {
          let component: Type<GuiComponent> | undefined;
          for (const className of this._resourceSchema.block_class_mro.split('__')) {
            component = EditorComponent.DATA_BLOCK_COMPONENTS_MAP[className];
            if (component) {
              break;
            }
          }
          if (!component) {
            this.resourceError = {
              message: 'UI not implemented for ' + this._resourceSchema.block_class_mro.replace(/__/g, ' &rarr; '),
            };
            this._resourceSchema = undefined;
            this._resourceData = undefined;
            return;
          }
          if (this._componentChangedSub) {
            this.componentSet$.next();
          }
          this._component = this.dataBlockUiHost.viewContainerRef.createComponent(component);
          this.componentSet$.next();
        }
        if (!reuseComponent || !schemaEquals(this._component!.instance.resourceSchema, this._resourceSchema)) {
          this._component!.setInput('resourceSchema', this._resourceSchema);
        }
      }
    }
    if (this._component) {
      this._component.setInput('resourceId', this._resourceId);
      this._component.setInput('resourceName', this._resourceName);
      this._component.setInput('resourceData', this._resourceData);
      this._component.setInput('resourceDescription', this._resourceDescription);
      this._component.setInput('hideName', this._hideName);
      this._component.setInput('hideBlockActions', this._hideBlockActions);
      this._component.setInput('disabled', this._disabled);
      this.cdr.markForCheck();
    }
  }

  _resourceDescription?: string;
  @Input()
  set resourceDescription(value: string | undefined) {
    this._resourceDescription = value;
    if (this._component) {
      this._component.setInput('resourceDescription', value);
    }
  }

  _hideName?: boolean;
  @Input()
  set hideName(value: boolean | undefined) {
    this._hideName = value;
    if (this._component) {
      this._component.setInput('hideName', value);
    }
  }

  _hideBlockActions?: boolean;
  @Input()
  set hideBlockActions(value: boolean | undefined) {
    this._hideBlockActions = value;
    if (this._component) {
      this._component.setInput('hideBlockActions', value);
    }
  }

  _disabled?: boolean;
  @Input()
  set disabled(value: boolean | undefined) {
    this._disabled = value;
    if (this._component) {
      this._component.setInput('disabled', value);
    }
  }

  @ViewChild(DataBlockUIDirective, { static: true }) dataBlockUiHost!: DataBlockUIDirective;

  _component: ComponentRef<GuiComponent> | null = null;
  _componentChangedSub: Subscription | null = null;

  private destroyed$: Subject<void> = new Subject<void>();
  private componentSet$: Subject<void> = new Subject<void>();

  resourceError: { class?: string; message: string } | null = null;

  constructor(
    readonly mainService: MainService,
    readonly changes: ChangesService,
    readonly cdr: ChangeDetectorRef,
  ) {}

  ngOnDestroy(): void {
    this.destroyed$.next();
    this.destroyed$.complete();
  }
}
