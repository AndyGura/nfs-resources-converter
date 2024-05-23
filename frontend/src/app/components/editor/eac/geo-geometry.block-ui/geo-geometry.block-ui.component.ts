import {
  AfterViewInit,
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  EventEmitter,
  Input,
  OnDestroy,
  Output,
} from '@angular/core';
import { GuiComponentInterface } from '../../gui-component.interface';
import { BehaviorSubject, debounceTime, filter, Subject, takeUntil } from 'rxjs';
import { EelDelegateService } from '../../../../services/eel-delegate.service';
import { MainService } from '../../../../services/main.service';
import { ObjViewerCustomControl } from '../../common/obj-viewer/obj-viewer.component';
import { Object3D } from 'three';
import { Nfs2CarMeshController } from './nfs2-car-mesh-controller';

@Component({
  selector: 'app-geo-geometry.block-ui',
  templateUrl: './geo-geometry.block-ui.component.html',
  styleUrls: ['./geo-geometry.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GeoGeometryBlockUiComponent implements GuiComponentInterface, AfterViewInit, OnDestroy {
  get resource(): Resource | null {
    return this._resource$.getValue();
  }

  @Input()
  set resource(value: Resource | null) {
    this._resource$.next(value);
  }

  _resource$: BehaviorSubject<Resource | null> = new BehaviorSubject<Resource | null>(null);

  @Output('changed') changed: EventEmitter<void> = new EventEmitter<void>();

  customControls: ObjViewerCustomControl[] = [];

  previewPaths$: BehaviorSubject<[string, string] | null> = new BehaviorSubject<[string, string] | null>(null);

  private readonly destroyed$: Subject<void> = new Subject<void>();

  constructor(
    private readonly eelDelegate: EelDelegateService,
    public readonly main: MainService,
    private readonly cdr: ChangeDetectorRef,
  ) {}

  async ngAfterViewInit() {
    this._resource$.pipe(takeUntil(this.destroyed$)).subscribe(async res => {
      this.previewPaths$.next(await this.loadPreviewFilePaths(res?.id));
    });
    this.main.dataBlockChange$
      .pipe(
        takeUntil(this.destroyed$),
        filter(([blockId, _]) => !!this.resource && blockId.startsWith(this.resource!.id)),
        debounceTime(1500),
      )
      .subscribe(async () => {
        this.previewPaths$.next(null);
        this.previewPaths$.next(await this.postTmpUpdates(this.resource?.id));
      });
  }

  async onObjectLoaded(obj: Object3D) {
    try {
      const meshController = new Nfs2CarMeshController(
        obj,
        this.previewPaths$.value![0].substring(0, this.previewPaths$.value![0].lastIndexOf('/')) + `/assets`,
      );
      let timeout: number | null = null;
      const setColor = (color: number) => {
        if (timeout) {
          clearTimeout(timeout);
        }
        timeout = setTimeout(() => (meshController.color = color), 50);
      };
      this.customControls = [
        {
          title: 'NFS2 car features',
          controls: [
            {
              label: 'Car color',
              type: 'color',
              value: 0x00ff00,
              change: c => setColor(c),
            },
          ],
        },
      ];
      if (meshController.hasWheels) {
        this.customControls[0].controls.push(
          {
            label: 'Car speed',
            type: 'radio',
            options: ['idle', 'slow', 'fast'],
            value: 'idle',
            change: v => {
              meshController.speed = v as any;
            },
          },
          {
            label: 'Steering angle',
            type: 'slider',
            minValue: -0.7,
            maxValue: 0.7,
            valueStep: 0.05,
            value: 0,
            change: v => {
              meshController.steeringAngle = v;
            },
          },
        );
      }
      this.cdr.markForCheck();
    } catch (err) {
      console.error(err);
    }
  }

  private serializerSettings = {
    geometry__save_obj: true,
    geometry__save_blend: false,
    geometry__export_to_gg_web_engine: false,
  };

  private async postTmpUpdates(blockId: string | undefined): Promise<[string, string] | null> {
    if (blockId) {
      const paths = await this.eelDelegate.serializeResourceTmp(
        blockId,
        Object.entries(this.main.changedDataBlocks)
          .filter(([id, _]) => id != '__has_external_changes__' && id.startsWith(blockId))
          .map(([id, value]) => {
            return { id, value };
          }),
        this.serializerSettings,
      );
      return [paths.find(x => x.endsWith('.obj'))!, paths.find(x => x.endsWith('.mtl'))!];
    }
    return null;
  }

  private async loadPreviewFilePaths(blockId: string | undefined): Promise<[string, string] | null> {
    if (blockId) {
      const paths = await this.eelDelegate.serializeResource(blockId, this.serializerSettings);
      return [paths.find(x => x.endsWith('.obj'))!, paths.find(x => x.endsWith('.mtl'))!];
    }
    return null;
  }

  previewObjectGroupFunc(objectName: string): string {
    if (objectName.startsWith('part_hp')) {
      return 'High-poly';
    } else if (objectName.startsWith('part_mp')) {
      return 'Medium-poly';
    } else if (objectName.startsWith('part_lp')) {
      return 'Low-poly';
    } else if (objectName.startsWith('part_res')) {
      return 'Reserved';
    } else {
      return objectName;
    }
  }

  ngOnDestroy(): void {
    this.destroyed$.next();
    this.destroyed$.complete();
  }
}
