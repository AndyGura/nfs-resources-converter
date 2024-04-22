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
import { Object3D } from 'three';
import { ObjViewerCustomControl } from '../../common/obj-viewer/obj-viewer.component';
import { Nfs1CarMeshController } from './nfs1-car-mesh-controller';

@Component({
  selector: 'app-orip-geometry-block-ui',
  templateUrl: './orip-geometry.block-ui.component.html',
  styleUrls: ['./orip-geometry.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class OripGeometryBlockUiComponent implements GuiComponentInterface, AfterViewInit, OnDestroy {
  get resource(): Resource | null {
    return this._resource$.getValue();
  }

  @Input()
  set resource(value: Resource | null) {
    this._resource$.next(value);
  }

  _resource$: BehaviorSubject<Resource | null> = new BehaviorSubject<Resource | null>(null);

  @Output('changed') changed: EventEmitter<void> = new EventEmitter<void>();

  previewPaths$: BehaviorSubject<[string, string] | null> = new BehaviorSubject<[string, string] | null>(null);

  private readonly destroyed$: Subject<void> = new Subject<void>();

  customControls: ObjViewerCustomControl[] = [];

  constructor(
    private readonly eelDelegate: EelDelegateService,
    private readonly mainService: MainService,
    private readonly cdr: ChangeDetectorRef,
  ) {}

  async ngAfterViewInit() {
    this._resource$.pipe(takeUntil(this.destroyed$)).subscribe(async res => {
      this.previewPaths$.next(await this.loadPreviewFilePaths(res?.id));
    });
    this.mainService.dataBlockChange$
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
    if ((this._resource$.value?.id || '').includes('.CFM__')) {
      try {
        const idParts = this.resource?.id.split('/')!;
        idParts.pop();
        idParts[idParts.length - 1] = '' + (+idParts[idParts.length - 1] + 1);
        const shpiData = await this.eelDelegate.retrieveValue(idParts.join('/') + '/data');
        const paletteIndex = shpiData.children_aliases.findIndex((x: string) => x === '!PAL');
        if (paletteIndex == -1) throw new Error('Not a car');
        const nfs1CarMesh = new Nfs1CarMeshController(
          obj,
          shpiData.children[paletteIndex],
          this._resource$.value!.id,
          this.previewPaths$.value![0],
        );
        this.customControls = [
          {
            title: 'TNFS car features',
            controls: [
              {
                label: 'Brake lights on',
                type: 'checkbox',
                value: false,
                change: v => {
                  nfs1CarMesh.tailLightsOn = v;
                },
              },
              {
                label: 'Car speed',
                type: 'radio',
                options: ['idle', 'slow', 'fast'],
                value: 'idle',
                change: v => {
                  nfs1CarMesh.speed = v as any;
                },
              },
            ],
          },
        ];
        this.cdr.markForCheck();
      } catch (err) {
        // pass
      }
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
        Object.entries(this.mainService.changedDataBlocks)
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

  ngOnDestroy(): void {
    this.destroyed$.next();
    this.destroyed$.complete();
  }
}
