import { ChangeDetectionStrategy, Component, inject, OnChanges, SimpleChanges } from '@angular/core';
import { GuiComponent } from '../../gui.component';
import { BehaviorSubject } from 'rxjs';
import { NavigationService } from '../../../../services/navigation.service';

@Component({
  selector: 'app-eacs-audio-block-ui',
  templateUrl: './eacs-audio.block-ui.component.html',
  styleUrls: ['./eacs-audio.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.Eager,
  standalone: false,
})
export class EacsAudioBlockUiComponent extends GuiComponent implements OnChanges {
  audioUrl$: BehaviorSubject<string | null> = new BehaviorSubject<string | null>(null);

  readonly navigation = inject(NavigationService);

  ngOnChanges(changes: SimpleChanges): void {
    if (changes.hasOwnProperty('resourceId') || changes.hasOwnProperty('resourceData')) {
      this.audioUrl$.next(null);
      if (this.resourceId) {
        this.mainService.api.serializeResource(this.resourceId).then(paths => {
          this.audioUrl$.next(paths.find(x => x.endsWith('.wav')) || null);
        });
      }
    }
  }
}
