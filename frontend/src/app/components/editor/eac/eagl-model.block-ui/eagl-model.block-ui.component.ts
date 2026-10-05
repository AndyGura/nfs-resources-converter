import { AfterViewInit, ChangeDetectionStrategy, Component, OnChanges, OnDestroy, SimpleChanges } from '@angular/core';
import { GuiComponent } from '../../gui.component';
import { BehaviorSubject, debounceTime, filter, Subject, takeUntil } from 'rxjs';

// NFS6 EAGL model (".o" file): 3D preview of the serialized OBJ, textured from the FSH file the model uses
@Component({
  selector: 'app-eagl-model-block-ui',
  templateUrl: './eagl-model.block-ui.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  standalone: false,
})
export class EaglModelBlockUiComponent extends GuiComponent implements AfterViewInit, OnChanges, OnDestroy {
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

  private async loadPreview() {
    this.previewPaths$.next(null);
    if (this.resourceId) {
      const paths = await this.mainService.api.serializeResource(this.resourceId, null, {
        geometry__save_obj: true,
        geometry__save_blend: false,
        geometry__export_to_gg_web_engine: false,
      });
      this.previewPaths$.next([paths.find(x => x.endsWith('.obj'))!, paths.find(x => x.endsWith('.mtl'))!]);
    }
  }

  ngOnDestroy(): void {
    this.destroyed$.next();
    this.destroyed$.complete();
  }
}
