import { AfterViewInit, ChangeDetectionStrategy, Component, OnChanges, OnDestroy, SimpleChanges } from '@angular/core';
import { GuiComponent } from '../../gui.component';
import { BehaviorSubject, debounceTime, filter, Subject, takeUntil } from 'rxjs';
import { ViewFilterOpts } from '../../common/obj-viewer/obj-viewer.component';
import { Object3D } from 'three';

@Component({
  selector: 'app-crp-geometry-block-ui',
  templateUrl: './crp-geometry.block-ui.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  standalone: false,
})
export class CrpGeometryBlockUiComponent extends GuiComponent implements AfterViewInit, OnChanges, OnDestroy {
  previewPaths$: BehaviorSubject<[string, string] | null> = new BehaviorSubject<[string, string] | null>(null);

  isTrack$: BehaviorSubject<boolean> = new BehaviorSubject<boolean>(false);

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
      this.isTrack$.next(this.resourceData?.resource_id === 'karT');
      this.loadPreview().then();
    }
  }

  // mesh name: <article name>_LOD<lod>_ai<animation frame>[_<texture>][_damaged]
  private static readonly MESH_NAME_REGEX = /^(.*_LOD\d+)_ai(\d+)(?:_.*?)?(_damaged)?$/;

  previewObjectGroupFunc(object: Object3D): string {
    const match = CrpGeometryBlockUiComponent.MESH_NAME_REGEX.exec(object.name);
    return match ? match[1] + (match[3] || '') : object.name;
  }

  previewAnimationFrameFunc(object: Object3D): number | null {
    const match = CrpGeometryBlockUiComponent.MESH_NAME_REGEX.exec(object.name);
    return match ? +match[2] : null;
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
  ];

  ngOnDestroy(): void {
    this.destroyed$.next();
    this.destroyed$.complete();
  }
}
