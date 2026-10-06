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
import { Object3D } from 'three';
import { ObjViewerCustomControl, ViewFilterOpts } from '../../common/obj-viewer/obj-viewer.component';
import { Nfs6CarDummy, Nfs6CarMeshController, Nfs6CarSkin } from './nfs6-car-mesh-controller';

// NFS6 EAGL model (".o" file): 3D preview of the serialized OBJ, textured from the FSH file the model uses. Car
// models (car.o in car.viv) are exported with "skins.json": they get LOD filter, skin switcher and wheel controls
@Component({
  selector: 'app-eagl-model-block-ui',
  templateUrl: './eagl-model.block-ui.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  standalone: false,
})
export class EaglModelBlockUiComponent extends GuiComponent implements AfterViewInit, OnChanges, OnDestroy {
  previewPaths$: BehaviorSubject<[string, string] | null> = new BehaviorSubject<[string, string] | null>(null);

  readonly cdr = inject(ChangeDetectorRef);

  customControls: ObjViewerCustomControl[] = [];
  previewViewFilters: ViewFilterOpts[] = [];

  private extraPath: string | null = null;
  private skinsPath: string | null = null;
  private meshController: Nfs6CarMeshController | null = null;

  private readonly destroyed$: Subject<void> = new Subject<void>();

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

  ngOnChanges(changes: SimpleChanges): void {
    if (changes.hasOwnProperty('resourceId') || changes.hasOwnProperty('resourceData')) {
      this.loadPreview().then();
    }
  }

  private async loadPreview() {
    this.previewPaths$.next(null);
    if (this.resourceId) {
      const paths = await this.mainService.api.serializeResource(this.resourceId, null, {
        geometry__save_obj: true,
        geometry__save_blend: false,
        geometry__export_to_gg_web_engine: false,
      });
      this.extraPath = paths.find(x => x.endsWith('_extra.json')) || null;
      this.skinsPath = paths.find(x => x.endsWith('/skins.json')) || null;
      const viewFilters = this.skinsPath ? [this.lodViewFilter] : [];
      if (viewFilters.length !== this.previewViewFilters.length) {
        this.previewViewFilters = viewFilters;
        this.cdr.markForCheck();
      }
      this.previewPaths$.next([paths.find(x => x.endsWith('.obj'))!, paths.find(x => x.endsWith('.mtl'))!]);
    }
  }

  async onObjectLoaded(obj: Object3D) {
    this.meshController?.dispose();
    this.meshController = null;
    this.customControls = [];
    if (!this.skinsPath) {
      this.cdr.markForCheck();
      return;
    }
    try {
      const loadJson = async (path: string | null) => {
        try {
          return path ? await (await fetch(path)).json() : null;
        } catch (err) {
          console.warn(`Cannot load ${path}`, err);
          return null;
        }
      };
      const dummies: Nfs6CarDummy[] = (await loadJson(this.extraPath))?.dummies || [];
      const skins: Nfs6CarSkin[] = (await loadJson(this.skinsPath)) || [];
      const meshController = new Nfs6CarMeshController(obj, dummies, skins);
      this.meshController = meshController;
      const controls: ObjViewerCustomControl['controls'] = [];
      if (meshController.skin && skins.length > 1) {
        const label = (skin: Nfs6CarSkin) => `${skin.label} (${skin.name})`;
        controls.push({
          label: 'Skin',
          type: 'radio',
          options: skins.map(label),
          value: label(skins[0]),
          change: v => (meshController.skin = skins.find(x => label(x) === v)?.name || null),
        });
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
      this.customControls = controls.length > 0 ? [{ title: 'NFS6 car features', controls }] : [];
    } catch (err) {
      console.error(err);
    }
    this.cdr.markForCheck();
  }

  // car mesh name: <lod>_<geometry index>_<geometry name>
  private readonly lodViewFilter: ViewFilterOpts = {
    name: 'LOD',
    filterGroups: ['High-poly', 'Medium-poly', 'Low-poly', 'Other'],
    checkedIndex: 0,
    pickFunction: object => {
      const index = ['hp_', 'mp_', 'lp_'].findIndex(x => object.name.startsWith(x));
      return index >= 0 ? index : 3;
    },
  };

  ngOnDestroy(): void {
    this.meshController?.dispose();
    this.destroyed$.next();
    this.destroyed$.complete();
  }
}
