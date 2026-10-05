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
import { Fce3CarMeshController, fceColorToRgb, FceDummy } from './fce3-car-mesh-controller';

@Component({
  selector: 'app-fce3-geometry-block-ui',
  templateUrl: './fce3-geometry.block-ui.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  standalone: false,
})
export class Fce3GeometryBlockUiComponent extends GuiComponent implements AfterViewInit, OnChanges, OnDestroy {
  customControls: ObjViewerCustomControl[] = [];

  previewPaths$: BehaviorSubject<[string, string] | null> = new BehaviorSubject<[string, string] | null>(null);

  readonly cdr = inject(ChangeDetectorRef);

  private extraPath: string | null = null;
  private meshController: Fce3CarMeshController | null = null;

  private readonly destroyed$: Subject<void> = new Subject<void>();

  ngOnChanges(changes: SimpleChanges): void {
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
      const data = this.resourceData;
      const primaryColor = data?.num_primary_colors > 0 ? fceColorToRgb(data.primary_colors[0]) : 0xff0000;
      const secondaryColor = data?.num_secondary_colors > 0 ? fceColorToRgb(data.secondary_colors[0]) : 0x808080;
      const meshController = new Fce3CarMeshController(obj, dummies, primaryColor, secondaryColor);
      this.meshController = meshController;
      const controls: ObjViewerCustomControl['controls'] = [];
      if (meshController.isPaintable) {
        controls.push(
          {
            label: 'Primary color',
            type: 'color',
            value: primaryColor,
            change: c => this.debounced(() => (meshController.primaryColor = c)),
          },
          {
            label: 'Secondary color',
            type: 'color',
            value: secondaryColor,
            change: c => this.debounced(() => (meshController.secondaryColor = c)),
          },
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
      this.customControls = controls.length > 0 ? [{ title: 'NFS3 car features', controls }] : [];
      this.cdr.markForCheck();
    } catch (err) {
      console.error(err);
    }
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

  // mesh name: <lod>_<part index>[_<part name>][__<texture>]
  previewObjectGroupFunc(object: Object3D): string {
    const match = /^(?:hp|mp|lp|tp|part)_\d+(?:_.*?)?(?=__|$)/.exec(object.name);
    return match ? match[0] : object.name;
  }

  public readonly previewViewFilter: ViewFilterOpts = {
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
