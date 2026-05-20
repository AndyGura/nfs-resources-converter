import { Component, EventEmitter, Input, OnChanges, Output, SimpleChanges } from '@angular/core';
import { GuiComponentInterface } from '../../gui-component.interface';
import { BehaviorSubject } from 'rxjs';
import { MainService } from '../../../../services/main.service';
import { NavigationService } from '../../../../services/navigation.service';
import { BlockData, BlockSchema } from '../../types';

@Component({
  selector: 'app-eacs-audio-block-ui',
  templateUrl: './eacs-audio.block-ui.component.html',
  styleUrls: ['./eacs-audio.block-ui.component.scss'],
})
export class EacsAudioBlockUiComponent implements GuiComponentInterface, OnChanges {
  @Input() resourceId?: string;
  @Input() resourceName?: string;
  @Input() resourceSchema?: BlockSchema;
  @Input() resourceData?: BlockData;
  @Input() resourceDescription?: string;

  @Input() hideName?: boolean;
  @Input() hideBlockActions?: boolean;
  @Input() disabled?: boolean;

  audioUrl$: BehaviorSubject<string | null> = new BehaviorSubject<string | null>(null);

  @Output('changed') changed: EventEmitter<void> = new EventEmitter<void>();

  constructor(public readonly main: MainService, public readonly navigation: NavigationService) {}

  ngOnChanges(changes: SimpleChanges): void {
    if (changes.hasOwnProperty('resourceId') || changes.hasOwnProperty('resourceData')) {
      this.audioUrl$.next(null);
      if (this.resourceId) {
        this.main.api.serializeResource(this.resourceId).then(paths => {
          this.audioUrl$.next(paths.find(x => x.endsWith('.wav')) || null);
        });
      }
    }
  }
}
