import {
  AfterViewInit,
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  inject,
  OnChanges,
  OnDestroy,
  SimpleChanges,
} from '@angular/core';
import { GuiComponent } from '../../gui.component';
import { BehaviorSubject, debounceTime, filter, Subject, takeUntil } from 'rxjs';
import { ObjViewerCustomControl, ViewFilterOpts } from '../../common/obj-viewer/obj-viewer.component';
import { Object3D } from 'three';
import { FceCarMeshController, fceColorToRgb, FceDummy, FceVersion } from './fce-car-mesh-controller';

@Component({
  selector: 'app-fce-geometry-block-ui',
  templateUrl: './fce-geometry.block-ui.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  standalone: false,
})
export class FceGeometryBlockUiComponent extends GuiComponent implements AfterViewInit, OnChanges, OnDestroy {
  customControls: ObjViewerCustomControl[] = [];

  previewPaths$: BehaviorSubject<[string, string] | null> = new BehaviorSubject<[string, string] | null>(null);

  readonly cdr = inject(ChangeDetectorRef);

  previewViewFilters: ViewFilterOpts[] = [];

  private extraPath: string | null = null;
  private meshController: FceCarMeshController | null = null;

  private readonly destroyed$: Subject<void> = new Subject<void>();

  ngOnChanges(changes: SimpleChanges): void {
    if (changes.hasOwnProperty('resourceSchema')) {
      // FCE4 has damaged copy of every mesh
      this.previewViewFilters =
        this.version === 4 ? [this.previewViewFilter, this.damageViewFilter] : [this.previewViewFilter];
    }
    if (changes.hasOwnProperty('resourceId') || changes.hasOwnProperty('resourceData')) {
      this.loadPreview().then();
    }
  }

  async ngAfterViewInit() {
    this.changes.change$
      .pipe(
        takeUntil(this.destroyed$),
        filter(x => !!(this.resourceId && x.startsWith(this.resourceId))),
        debounceTime(150),
      )
      .subscribe(async () => {
        await this.loadPreview();
      });
  }

  async onObjectLoaded(obj: Object3D) {
    try {
      this.meshController?.dispose();
      let dummies: FceDummy[] = [];
      if (this.extraPath) {
        try {
          dummies = (await (await fetch(this.extraPath)).json()).dummies || [];
        } catch (err) {
          console.warn('Cannot load FCE dummies', err);
        }
      }
      // default paint is the first color of the car
      const paints = this.paints;
      const meshController = new FceCarMeshController(
        obj,
        this.version,
        dummies,
        paints.map(x => x.color),
      );
      this.meshController = meshController;
      const controls: ObjViewerCustomControl['controls'] = [];
      if (meshController.isPaintable) {
        paints.forEach(({ label, color }, i) =>
          controls.push({
            label,
            type: 'color',
            value: color,
            change: c => this.debounced(() => meshController.setColor(i, c)),
          }),
        );
      }
      if (meshController.hasLights) {
        controls.push({
          label: 'Show lights',
          type: 'checkbox',
          value: meshController.showLights,
          change: v => (meshController.showLights = v),
        });
      }
      if (meshController.hasWheels) {
        controls.push(
          {
            label: 'Car speed',
            type: 'radio',
            options: ['idle', 'slow', 'fast'],
            value: 'idle',
            change: v => (meshController.speed = v as any),
          },
          {
            label: 'Steering angle',
            type: 'slider',
            minValue: -0.7,
            maxValue: 0.7,
            valueStep: 0.05,
            value: 0,
            change: v => (meshController.steeringAngle = v),
          },
        );
      }
      this.customControls = controls.length > 0 ? [{ title: `NFS${this.version} car features`, controls }] : [];
      this.cdr.markForCheck();
    } catch (err) {
      console.error(err);
    }
  }

  get version(): FceVersion {
    return this.resourceSchema?.block_class_mro?.startsWith('Fce4Geometry') ? 4 : 3;
  }

  /** Colors of car paint: the first color set of the model */
  private get paints(): { label: string; color: number }[] {
    const data = this.resourceData;
    const paint = (label: string, colorsKey: string, numColors: number, fallback: number) => ({
      label,
      color: numColors > 0 ? fceColorToRgb(data[colorsKey][0]) : fallback,
    });
    if (this.version === 4) {
      return [
        paint('Primary color', 'primary_colors', data?.num_colors, 0xff0000),
        paint('Interior color', 'interior_colors', data?.num_colors, 0x404040),
        paint('Secondary color', 'secondary_colors', data?.num_colors, 0x808080),
        paint('Driver hair color', 'driver_hair_colors', data?.num_colors, 0x302010),
      ];
    }
    return [
      paint('Primary color', 'primary_colors', data?.num_primary_colors, 0xff0000),
      paint('Secondary color', 'secondary_colors', data?.num_secondary_colors, 0x808080),
    ];
  }

  private debounceTimer: any = null;

  private debounced(func: () => void) {
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer);
    }
    this.debounceTimer = setTimeout(func, 50);
  }

  private serializerSettings = {
    geometry__save_obj: true,
    geometry__save_blend: false,
    geometry__export_to_gg_web_engine: false,
  };

  private async loadPreview() {
    this.previewPaths$.next(null);
    if (this.resourceId) {
      const paths = await this.mainService.api.serializeResource(this.resourceId, null, this.serializerSettings);
      this.extraPath = paths.find(x => x.endsWith('_extra.json')) || null;
      this.previewPaths$.next([paths.find(x => x.endsWith('.obj'))!, paths.find(x => x.endsWith('.mtl'))!]);
    }
  }

  // mesh name: <lod>_<part index>[_<part name>][__<texture>][_damaged]
  previewObjectGroupFunc(object: Object3D): string {
    const match = /^(?:hp|mp|lp|tp|part)_\d+(?:_.*?)?(?=__|_damaged$|$)/.exec(object.name);
    return match ? match[0] : object.name;
  }

  private readonly damageViewFilter: ViewFilterOpts = {
    name: 'Damage',
    filterGroups: ['Not damaged', 'Damaged'],
    checkedIndex: 0,
    pickFunction: object => (object.name.endsWith('_damaged') ? 1 : 0),
  };

  private readonly previewViewFilter: ViewFilterOpts = {
    name: 'LOD',
    filterGroups: ['High-poly', 'Medium-poly', 'Low-poly', 'Tiny', 'Other'],
    checkedIndex: 0,
    pickFunction: object => {
      const index = ['hp_', 'mp_', 'lp_', 'tp_'].findIndex(x => object.name.startsWith(x));
      return index >= 0 ? index : 4;
    },
  };

  ngOnDestroy(): void {
    this.meshController?.dispose();
    this.destroyed$.next();
    this.destroyed$.complete();
  }
}
