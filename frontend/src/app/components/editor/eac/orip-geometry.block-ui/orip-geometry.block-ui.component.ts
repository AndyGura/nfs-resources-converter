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
import { ObjViewerCustomControl } from '../../common/obj-viewer/obj-viewer.component';
import { steeringControl, wheelSpeedControl } from '../../common/obj-viewer/car-preview-controls';
import { TnfsCarColors, TnfsCarMeshController, TnfsLightBarMode } from './tnfs-car-mesh-controller';

// how the preview draws palette indices 250..253: as the game does on a car, on a cop (idle, in a chase), or as the PNGs
const LIGHT_BAR_OPTIONS: Record<string, [TnfsLightBarMode, boolean]> = {
  'Black (car)': ['black', false],
  'Siren (cop)': ['siren', false],
  'Siren flashing': ['siren', true],
  Texture: ['texture', false],
};

@Component({
  selector: 'app-orip-geometry-block-ui',
  templateUrl: './orip-geometry.block-ui.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  standalone: false,
})
export class OripGeometryBlockUiComponent extends GuiComponent implements AfterViewInit, OnChanges, OnDestroy {
  previewPaths$: BehaviorSubject<[string, string] | null> = new BehaviorSubject<[string, string] | null>(null);

  customControls: ObjViewerCustomControl[] = [];

  readonly cdr = inject(ChangeDetectorRef);
  private meshController: TnfsCarMeshController | null = null;
  private tyresTimer: number | undefined = undefined;
  destroyed$: Subject<void> = new Subject<void>();

  ngAfterViewInit(): void {
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

  ngOnDestroy(): void {
    this.disposeMeshController();
    this.destroyed$.next();
    this.destroyed$.complete();
  }

  async onObjectLoaded(obj: Object3D) {
    if (this.resourceId && this.resourceId.includes('.CFM__')) {
      try {
        const objPath = this.previewPaths$.value![0];
        const assetsPath = objPath.substring(0, objPath.lastIndexOf('/')) + `/assets`;
        // written by the converter next to the textures, as nfs-web gets it
        let carColors: TnfsCarColors | null = null;
        try {
          const response = await fetch(`${assetsPath}/car_colors.json`);
          carColors = response.ok ? await response.json() : null;
        } catch {
          carColors = null;
        }
        this.disposeMeshController();
        const meshController = new TnfsCarMeshController(obj, carColors, assetsPath);
        this.meshController = meshController;
        // the tyre textures animate as if the car drove along x at the wheel speed, as nfs-web's /car-tex-debug
        let speed = 0;
        let x = 0;
        const dt = 1000 / 30;
        this.tyresTimer = setInterval(() => {
          x += (speed * 1.25 * dt) / 1000;
          meshController.updateTyres(dt, speed, 0, 0, { x, y: 0, z: 0 });
          meshController.updateLights(dt);
        }, dt) as any as number;
        this.customControls = [
          {
            title: 'TNFS car features',
            controls: [
              {
                label: 'Brake lights on',
                type: 'checkbox',
                value: false,
                change: v => {
                  meshController.tailLightsOn = v;
                },
              },
              {
                label: 'Colors 250-253 (light bar)',
                type: 'radio',
                options: Object.keys(LIGHT_BAR_OPTIONS),
                value: 'Black (car)',
                change: v => {
                  const [mode, sirenActive] = LIGHT_BAR_OPTIONS[v];
                  meshController.lightBar = mode;
                  meshController.sirenActive = sirenActive;
                },
              },
              ...(meshController.hasWheels
                ? [wheelSpeedControl(v => (speed = v)), steeringControl(v => (meshController.steeringAngle = v))]
                : []),
            ],
          },
        ];
        this.cdr.markForCheck();
      } catch (err) {
        // pass
      }
    }
  }

  private disposeMeshController() {
    clearInterval(this.tyresTimer);
    this.tyresTimer = undefined;
    this.meshController?.dispose();
    this.meshController = null;
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
      this.previewPaths$.next([paths.find(x => x.endsWith('.obj'))!, paths.find(x => x.endsWith('.mtl'))!]);
    }
  }
}
