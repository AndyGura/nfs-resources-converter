import { ChangeDetectionStrategy, Component } from '@angular/core';
import { EelDelegateService } from './services/eel-delegate.service';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MainService } from './services/main.service';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AppComponent {

  constructor(readonly eelDelegate: EelDelegateService,
              readonly mainService: MainService,
              private readonly snackBar: MatSnackBar) {
  }

  Object = Object;

  async saveResource() {
    try {
      const changes = Object.entries(this.mainService.changedDataBlocks);
      await this.eelDelegate.saveFile(changes.map(([id, value]) => {
        return { id, value };
      }));
      this.snackBar.open('File Saved!', 'OK', { duration: 1500 });
      Object.keys(this.mainService.changedDataBlocks).forEach(key => {
        delete this.mainService.changedDataBlocks[key];
      });
    } catch (err: any) {
      this.snackBar.open('Error while saving file! ' + err.errorText, 'OK :(', { duration: 1500 });
    }
  }

}
