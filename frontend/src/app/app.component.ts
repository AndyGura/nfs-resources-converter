import { ChangeDetectionStrategy, Component, OnChanges, OnInit, SimpleChanges } from '@angular/core';
import { EelDelegateService } from './services/eel-delegate.service';
import { BehaviorSubject } from 'rxjs';
import { MatSnackBar } from '@angular/material/snack-bar';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AppComponent implements OnInit {
  resourceData$: BehaviorSubject<ReadData | null> = new BehaviorSubject<ReadData | null>(null);
  resourceError$: BehaviorSubject<ReadError | null> = new BehaviorSubject<ReadError | null>(null);

  constructor(readonly eelDelegate: EelDelegateService,
              private readonly snackBar: MatSnackBar) {
  }

  ngOnInit(): void {
    this.eelDelegate.openedResource$.subscribe((value) => {
      if (!value) {
        this.resourceData$.next(null);
        this.resourceError$.next(null);
      } else if ((value as any).block_class_mro) {
        this.resourceData$.next(value as ReadData);
        this.resourceError$.next(null);
      } else {
        this.resourceData$.next(null);
        this.resourceError$.next(value as ReadError);
      }
    });
  }

  async saveResource() {
    try {
      await this.eelDelegate.saveFile();
      this.snackBar.open('File Saved!');
    } catch (err: any) {
      this.snackBar.open('Error while saving file! ' + err.errorText);
    }
  }

}
