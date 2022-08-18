import { ChangeDetectionStrategy, Component, OnChanges, OnInit, SimpleChanges } from '@angular/core';
import { EelDelegateService } from './services/eel-delegate.service';
import { BehaviorSubject } from 'rxjs';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AppComponent implements OnInit {
  resourceData$: BehaviorSubject<ReadData | null> = new BehaviorSubject<ReadData | null>(null);

  constructor(readonly eelDelegate: EelDelegateService) {
  }

  ngOnInit(): void {
    this.eelDelegate.openedResource$.subscribe(this.resourceData$);
  }

}
