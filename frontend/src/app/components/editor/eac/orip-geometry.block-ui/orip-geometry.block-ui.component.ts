import {
  AfterViewInit,
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  EventEmitter,
  Input,
  OnChanges,
  OnDestroy,
  Output,
  SimpleChanges,
} from '@angular/core';
import { GuiComponentInterface } from '../../gui-component.interface';
import { BehaviorSubject, debounceTime, filter, Subject, takeUntil } from 'rxjs';
import { MainService } from '../../../../services/main.service';
import { Object3D } from 'three';
import { ObjViewerCustomControl } from '../../common/obj-viewer/obj-viewer.component';
import { TnfsCarMeshController } from './tnfs-car-mesh-controller';
import { BlockData, BlockSchema } from '../../types';

@Component({
  selector: 'app-orip-geometry-block-ui',
  templateUrl: './orip-geometry.block-ui.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class OripGeometryBlockUiComponent implements GuiComponentInterface, AfterViewInit, OnDestroy, OnChanges {
  @Input() resourceId?: string;
  @Input() resourceName?: string;
  @Input() resourceSchema?: BlockSchema;
  @Input() resourceData?: BlockData;
  @Input() resourceDescription?: string;

  @Input() hideName?: boolean;
  @Input() hideBlockActions?: boolean;
  @Input() disabled?: boolean;

  @Output('changed') changed: EventEmitter<void> = new EventEmitter<void>();

  previewPaths$: BehaviorSubject<[string, string] | null> = new BehaviorSubject<[string, string] | null>(null);

  private readonly destroyed$: Subject<void> = new Subject<void>();

  customControls: ObjViewerCustomControl[] = [];

  constructor(private readonly mainService: MainService, private readonly cdr: ChangeDetectorRef) {}

  ngOnChanges(changes: SimpleChanges): void {
    if (changes.hasOwnProperty('resourceId') || changes.hasOwnProperty('resourceData')) {
      this.loadPreview().then();
    }
  }

  async ngAfterViewInit() {
    this.mainService.dataBlockChange$
      .pipe(
        takeUntil(this.destroyed$),
        filter(([blockId, _]) => !!this.resourceId && blockId.startsWith(this.resourceId)),
        debounceTime(1000),
      )
      .subscribe(async () => {
        await this.loadPreview();
      });
  }

  async onObjectLoaded(obj: Object3D) {
    if (this.resourceId && this.resourceId.includes('.CFM__')) {
      try {
        const idParts = this.resourceId.split('/')!;
        idParts.pop();
        idParts[idParts.length - 1] = '' + (+idParts[idParts.length - 1] + 1);
        const shpiData = await this.mainService.api.retrieveValue(idParts.join('/') + '/data');
        const paletteIndex = shpiData.children_aliases.findIndex((x: string) => x === '!PAL');
        if (paletteIndex == -1) throw new Error('Not a car');
        const meshController = new TnfsCarMeshController(
          obj,
          shpiData.children[paletteIndex].data.colors[254] >>> 8,
          this.previewPaths$.value![0].substring(0, this.previewPaths$.value![0].lastIndexOf('/')) + `/assets`,
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
                  meshController.tailLightsOn = v;
                },
              },
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

  private async loadPreview() {
    this.previewPaths$.next(null);
    if (this.resourceId) {
      const paths = await this.mainService.api.serializeResource(this.resourceId, null, this.serializerSettings);
      this.previewPaths$.next([paths.find(x => x.endsWith('.obj'))!, paths.find(x => x.endsWith('.mtl'))!]);
    }
  }

  ngOnDestroy(): void {
    this.destroyed$.next();
    this.destroyed$.complete();
  }
}
