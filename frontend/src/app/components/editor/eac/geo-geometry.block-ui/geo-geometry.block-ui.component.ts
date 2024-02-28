import {
  AfterViewInit,
  ChangeDetectionStrategy,
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

  previewPaths$: BehaviorSubject<[string, string] | null> = new BehaviorSubject<[string, string] | null>(null);

  private readonly destroyed$: Subject<void> = new Subject<void>();

  constructor(private readonly eelDelegate: EelDelegateService, private readonly mainService: MainService) {}

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

  private serializerSettings = {
    geometry__save_obj: true,
    geometry__save_blend: false,
    geometry__export_to_gg_web_engine: false,
    geometry__replace_car_wheel_with_dummies: false,
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
