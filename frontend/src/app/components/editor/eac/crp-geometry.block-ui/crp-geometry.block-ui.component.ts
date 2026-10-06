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
import { Nfs5CarMeshController } from './nfs5-car-mesh-controller';

// NFS5 CRP geometry: cars open in the 3D model viewer, tracks ("karT") in the shared track viewer
@Component({
  selector: 'app-crp-geometry-block-ui',
  templateUrl: './crp-geometry.block-ui.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  standalone: false,
})
export class CrpGeometryBlockUiComponent extends GuiComponent implements AfterViewInit, OnChanges, OnDestroy {
  previewPaths$: BehaviorSubject<[string, string] | null> = new BehaviorSubject<[string, string] | null>(null);

  isTrack$: BehaviorSubject<boolean> = new BehaviorSubject<boolean>(false);

  customControls: ObjViewerCustomControl[] = [];

  readonly cdr = inject(ChangeDetectorRef);

  private meshController: Nfs5CarMeshController | null = null;

  // filter of default car parts, by loaded object
  private readonly defaultPartFilters = new WeakMap<Object3D, (article: string) => boolean>();

  private readonly destroyed$: Subject<void> = new Subject<void>();

  async ngAfterViewInit() {
    this.changes.change$
      .pipe(
        takeUntil(this.destroyed$),
        filter(x => !this.isTrack$.value && !!(this.resourceId && x.startsWith(this.resourceId))),
        debounceTime(150),
      )
      .subscribe(async () => {
        await this.loadPreview();
      });
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes.hasOwnProperty('resourceId') || changes.hasOwnProperty('resourceData')) {
      this.isTrack$.next(this.resourceData?.resource_id === 'karT');
      this.loadPreview().then();
    }
  }

  // mesh name: <article name>_LOD<lod>_ai<animation frame>[_<texture>][_damaged]
  private static readonly MESH_NAME_REGEX = /^(.*_LOD\d+)_ai(\d+)(?:_(?!damaged$).*?)?(_damaged)?$/;

  previewObjectGroupFunc(object: Object3D): string {
    const match = CrpGeometryBlockUiComponent.MESH_NAME_REGEX.exec(object.name);
    return match ? match[1] + (match[3] || '') : object.name;
  }

  previewAnimationFrameFunc(object: Object3D): number | null {
    const match = CrpGeometryBlockUiComponent.MESH_NAME_REGEX.exec(object.name);
    return match ? +match[2] : null;
  }

  onObjectLoaded(obj: Object3D) {
    try {
      this.meshController?.dispose();
      const meshController = new Nfs5CarMeshController(obj);
      this.meshController = meshController;
      this.customControls = meshController.hasWheels
        ? [
            {
              title: 'NFS5 car features',
              controls: [
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
              ],
            },
          ]
        : [];
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
    if (this.resourceId && !this.isTrack$.value) {
      const paths = await this.mainService.api.serializeResource(this.resourceId, null, this.serializerSettings);
      this.previewPaths$.next([paths.find(x => x.endsWith('.obj'))!, paths.find(x => x.endsWith('.mtl'))!]);
    }
  }

  public readonly previewViewFilters: ViewFilterOpts[] = [
    {
      name: 'LOD',
      filterGroups: [
        'Uncategorized',
        'Lod level 0',
        'LOD level 1',
        'LOD level 2',
        'LOD level 3',
        'LOD level 4',
        'LOD level 5',
        'LOD level 6',
        'LOD level 7',
      ],
      checkedIndex: 0,
      pickFunction: object => {
        try {
          let lodIndex = /_LOD(\d+)_/gi.exec(object.name)![1];
          if (+lodIndex <= 7) {
            return +lodIndex + 1;
          }
        } catch {}
        return 0;
      },
    },
    {
      name: 'Damage',
      filterGroups: ['Not damaged', 'Damaged'],
      checkedIndex: 0,
      pickFunction: object => {
        return object.name.endsWith('_damaged') ? 1 : 0;
      },
    },
    {
      // a car has every variant of its parts (body kits, spoiler states, cabrio roof, drivers)
      name: 'Parts',
      filterGroups: ['Default look', 'Variants, driver'],
      checkedIndex: 0,
      pickFunction: object => {
        const article = Nfs5CarMeshController.parseMeshName(object.name)?.article;
        if (!article || !object.parent) {
          return 0;
        }
        let isDefault = this.defaultPartFilters.get(object.parent);
        if (!isDefault) {
          isDefault = Nfs5CarMeshController.defaultArticleFilter(
            object.parent.children.map(x => Nfs5CarMeshController.parseMeshName(x.name)?.article || ''),
          );
          this.defaultPartFilters.set(object.parent, isDefault);
        }
        return isDefault(article) ? 0 : 1;
      },
    },
  ];

  ngOnDestroy(): void {
    this.meshController?.dispose();
    this.destroyed$.next();
    this.destroyed$.complete();
  }
}
