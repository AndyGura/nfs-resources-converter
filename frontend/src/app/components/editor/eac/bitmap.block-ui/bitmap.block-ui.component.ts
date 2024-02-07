import {
  AfterViewInit,
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  EventEmitter,
  Input,
  Output,
} from '@angular/core';
import { GuiComponentInterface } from '../../gui-component.interface';
import { EelDelegateService } from '../../../../services/eel-delegate.service';
import { BehaviorSubject, Subject, takeUntil } from 'rxjs';
import { MainService } from '../../../../services/main.service';

@Component({
  selector: 'app-bitmap-block-ui',
  templateUrl: './bitmap.block-ui.component.html',
  styleUrls: ['./bitmap.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BitmapBlockUiComponent implements GuiComponentInterface, AfterViewInit {
  _resource$: BehaviorSubject<Resource | null> = new BehaviorSubject<Resource | null>(null);
  imageUrl$: BehaviorSubject<string | null> = new BehaviorSubject<string | null>(null);

  @Input() set resource(value: Resource | null) {
    this._resource$.next(value);
  }

  get resource(): Resource | null {
    return this._resource$.getValue();
  }

  private readonly destroyed$: Subject<void> = new Subject<void>();

  @Output('changed') changed: EventEmitter<void> = new EventEmitter<void>();

  constructor(
    private readonly eelDelegate: EelDelegateService,
    private readonly cdr: ChangeDetectorRef,
    public readonly main: MainService,
  ) {}

  async ngAfterViewInit() {
    this._resource$.pipe(takeUntil(this.destroyed$)).subscribe(async res => {
      if (res) {
        const paths = await this.eelDelegate.serializeResource(res.id);
        this.imageUrl$.next(paths.find(x => x.endsWith('.png')) || null);
      } else {
        this.imageUrl$.next(null);
      }
    });
  }

  ngOnDestroy(): void {
    this.destroyed$.next();
    this.destroyed$.complete();
  }
}
