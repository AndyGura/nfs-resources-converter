import { AfterViewInit, Component, EventEmitter, Input, OnDestroy, Output } from '@angular/core';
import { GuiComponentInterface } from '../../gui-component.interface';
import { BehaviorSubject, Subject, takeUntil } from 'rxjs';
import { EelDelegateService } from '../../../../services/eel-delegate.service';
import { MainService } from '../../../../services/main.service';

@Component({
  selector: 'app-eacs-audio.block-ui',
  templateUrl: './eacs-audio.block-ui.component.html',
  styleUrls: ['./eacs-audio.block-ui.component.scss'],
})
export class EacsAudioBlockUiComponent implements GuiComponentInterface, AfterViewInit, OnDestroy {
  _resource$: BehaviorSubject<Resource | null> = new BehaviorSubject<Resource | null>(null);
  audioUrl$: BehaviorSubject<string | null> = new BehaviorSubject<string | null>(null);

  @Input() set resource(value: Resource | null) {
    this._resource$.next(value);
  }

  get resource(): Resource | null {
    return this._resource$.getValue();
  }

  @Input() resourceDescription: string = '';

  @Input() hideBlockActions: boolean = false;

  private readonly destroyed$: Subject<void> = new Subject<void>();

  @Output('changed') changed: EventEmitter<void> = new EventEmitter<void>();

  constructor(private readonly eelDelegate: EelDelegateService, public readonly main: MainService) {}

  async ngAfterViewInit() {
    this._resource$.pipe(takeUntil(this.destroyed$)).subscribe(async res => {
      this.audioUrl$.next(null);
      if (res) {
        const paths = await this.eelDelegate.serializeResource(res.id, { audio__save_car_sfx_loops: false });
        this.audioUrl$.next(paths.find(x => x.endsWith('.mp3')) || null);
      }
    });
  }

  ngOnDestroy(): void {
    this.destroyed$.next();
    this.destroyed$.complete();
  }
}
