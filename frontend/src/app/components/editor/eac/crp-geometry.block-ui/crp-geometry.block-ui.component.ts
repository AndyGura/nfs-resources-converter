import {
  AfterViewInit,
  ChangeDetectionStrategy,
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
import { BlockData, BlockSchema } from '../../types';
import { ViewFilterOpts } from '../../common/obj-viewer/obj-viewer.component';

@Component({
  selector: 'app-crp-geometry-block-ui',
  templateUrl: './crp-geometry.block-ui.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CrpGeometryBlockUiComponent implements GuiComponentInterface, AfterViewInit, OnDestroy, OnChanges {
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

  isTrack$: BehaviorSubject<boolean> = new BehaviorSubject<boolean>(false);

  private readonly destroyed$: Subject<void> = new Subject<void>();

  constructor(private readonly mainService: MainService) {}

  ngOnChanges(changes: SimpleChanges): void {
    if (changes.hasOwnProperty('resourceId') || changes.hasOwnProperty('resourceData')) {
      this.isTrack$.next(this.resourceData?.resource_id === 'karT');
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
