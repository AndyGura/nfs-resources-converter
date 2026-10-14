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
import { TnfsCarMeshController } from './tnfs-car-mesh-controller';

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
        const idParts = this.resourceId.split('/')!;
        idParts[idParts.length - 3] = '' + (+idParts[idParts.length - 3] + 1);
        const shpiData = await this.mainService.api.retrieveValue(idParts.join('/'));
        const palette = shpiData.children.find((x: any) => x.alias === '!PAL');
        if (!palette) throw new Error('Not a car');
        this.disposeMeshController();
        const meshController = new TnfsCarMeshController(
          obj,
          palette.item.data.colors.data[254] >>> 8,
          this.previewPaths$.value![0].substring(0, this.previewPaths$.value![0].lastIndexOf('/')) + `/assets`,
        );
        this.meshController = meshController;
        // the tyre textures animate as if the car drove along x at the wheel speed, as nfs-web's /car-tex-debug
        let speed = 0;
        let x = 0;
        const dt = 1000 / 30;
        this.tyresTimer = setInterval(() => {
          x += (speed * 1.25 * dt) / 1000;
          meshController.updateTyres(dt, speed, 0, 0, { x, y: 0, z: 0 });
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
              wheelSpeedControl(v => (speed = v)),
              steeringControl(v => (meshController.steeringAngle = v)),
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
