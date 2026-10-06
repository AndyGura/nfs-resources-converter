import { AfterViewInit, ChangeDetectionStrategy, Component, OnChanges, OnDestroy, SimpleChanges } from '@angular/core';
import { GuiComponent } from '../../gui.component';
import { BehaviorSubject, debounceTime, filter, Subject, takeUntil } from 'rxjs';
import { ViewFilterOpts } from '../../common/obj-viewer/obj-viewer.component';

@Component({
  selector: 'app-nfsu-bin-geometry-block-ui',
  templateUrl: './nfsu-bin-geometry.block-ui.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  standalone: false,
})
export class NfsuBinGeometryBlockUiComponent extends GuiComponent implements AfterViewInit, OnChanges, OnDestroy {
  previewPaths$: BehaviorSubject<[string, string] | null> = new BehaviorSubject<[string, string] | null>(null);

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

  // object name is "<mesh name>__<texture name>", mesh name is "<CAR>_<part>_<LOD letter>", e.g.
  // "SUPRA_KIT00_FRONT_BUMPER_A". The name is cut to 27 characters, so the LOD letter can be missing
  private static meshName(object: { name: string }): string {
    return object.name.split('__')[0];
  }

  // one list entry per mesh, whatever amount of textures it has
  public readonly previewObjectGroupFunc = (object: { name: string }) => NfsuBinGeometryBlockUiComponent.meshName(object);

  public readonly previewViewFilters: ViewFilterOpts[] = [
    {
      name: 'LOD',
      filterGroups: ['A', 'B', 'C', 'D', '?'],
      checkedIndex: 0,
      pickFunction: object => {
        const name = NfsuBinGeometryBlockUiComponent.meshName(object);
        switch (name.substring(name.length - 2)) {
          case '_A':
            return 0;
          case '_B':
            return 1;
          case '_C':
            return 2;
          case '_D':
            return 3;
        }
        return 4;
      },
    },
    {
      name: 'Parts',
      filterGroups: ['Stock', 'Body kits', 'Widebody kits', 'Aftermarket', 'Decals'],
      checkedIndex: 0,
      pickFunction: object => {
        const part = NfsuBinGeometryBlockUiComponent.meshName(object).split('_')[1] || '';
        if (part === 'BASE' || part === 'KIT00') {
          return 0;
        }
        if (/^KIT\d+$/.test(part)) {
          return 1;
        }
        if (/^KITW\d+$/.test(part)) {
          return 2;
        }
        if (/^STYLE\d+$/.test(part)) {
          return 3;
        }
        return 4;
      },
    },
  ];

  ngOnDestroy(): void {
    this.destroyed$.next();
    this.destroyed$.complete();
  }
}
