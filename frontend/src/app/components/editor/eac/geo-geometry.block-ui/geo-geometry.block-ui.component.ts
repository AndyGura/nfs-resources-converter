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
import { Nfs2CarMeshController } from './nfs2-car-mesh-controller';

@Component({
  selector: 'app-geo-geometry.block-ui',
  templateUrl: './geo-geometry.block-ui.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  standalone: false,
})
export class GeoGeometryBlockUiComponent extends GuiComponent implements AfterViewInit, OnChanges, OnDestroy {
  customControls: ObjViewerCustomControl[] = [];

  previewPaths$: BehaviorSubject<[string, string] | null> = new BehaviorSubject<[string, string] | null>(null);

  readonly cdr = inject(ChangeDetectorRef);

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
      const meshController = new Nfs2CarMeshController(
        obj,
        this.previewPaths$.value![0].substring(0, this.previewPaths$.value![0].lastIndexOf('/')) + `/assets`,
      );
      let timeout: number | null = null;
      const setColor = (color: number) => {
        if (timeout) {
          clearTimeout(timeout);
        }
        timeout = setTimeout(() => (meshController.color = color), 50) as any as number;
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

  private async loadPreview() {
    this.previewPaths$.next(null);
    if (this.resourceId) {
      const paths = await this.mainService.api.serializeResource(this.resourceId, null, this.serializerSettings);
      this.previewPaths$.next([paths.find(x => x.endsWith('.obj'))!, paths.find(x => x.endsWith('.mtl'))!]);
    }
  }

  previewObjectGroupFunc(object: Object3D): string {
    try {
      let index = /^part_[h|m|l]p_(\d+)_/gi.exec(object.name)![1];
      return `part_${index}`;
    } catch {
      return object.name;
    }
  }

  public readonly previewViewFilter: ViewFilterOpts = {
    name: 'LOD',
    filterGroups: ['High-poly', 'Medium-poly', 'Low-poly', 'Reserved', 'Unknown'],
    checkedIndex: 0,
    pickFunction: object => {
      if (object.name.startsWith('part_hp')) {
        return 0;
      } else if (object.name.startsWith('part_mp')) {
        return 1;
      } else if (object.name.startsWith('part_lp')) {
        return 2;
      } else if (object.name.startsWith('part_res')) {
        return 3;
      } else {
        return 4;
      }
    },
  };

  ngOnDestroy(): void {
    this.destroyed$.next();
    this.destroyed$.complete();
  }
}
