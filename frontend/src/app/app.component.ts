import { ChangeDetectionStrategy, ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MainService } from './services/main.service';
import { MatDialog } from '@angular/material/dialog';
import { ConfirmDialogComponent } from './components/confirm.dialog/confirm.dialog.component';
import { firstValueFrom } from 'rxjs';
import { NavigationService } from './services/navigation.service';
import { ConverterComponent } from './components/converter/converter.component';
import { ConfigComponent } from './components/config/config.component';
import { NewFileDialogComponent } from './components/new-file.dialog/new-file.dialog.component';
import { environment } from '../environments/environment';
import { ChangeEntry, ChangesService } from './services/changes.service';
import { ApiDelegateService } from './services/api/api-delegate.service';
import { Title } from '@angular/platform-browser';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  standalone: false,
})
export class AppComponent implements OnInit {
  readonly isProduction = environment.production;

  constructor(
    readonly mainService: MainService,
    readonly api: ApiDelegateService,
    readonly changes: ChangesService,
    readonly dialog: MatDialog,
    readonly navigation: NavigationService,
    private readonly snackBar: MatSnackBar,
    private readonly cdr: ChangeDetectorRef,
    private readonly titleService: Title,
  ) {}

  ngOnInit() {
    this.api.openedResourcePath$.subscribe(path => {
      if (path) {
        this.titleService.setTitle(`${this.getFileName(path)} | NFS Resources Converter`);
      } else {
        this.titleService.setTitle('NFS Resources Converter');
      }
    });
  }

  async openFile() {
    const fileNames = await this.mainService.api.openFileDialog();
    if (fileNames.length > 0) {
      await this.mainService.api.openFile(fileNames[0], true);
    }
  }

  async createNewFile() {
    const dialogRef = this.dialog.open(NewFileDialogComponent, {
      width: '400px',
    });
    const format = await firstValueFrom(dialogRef.afterClosed());
    if (format) {
      const path = await this.mainService.api.saveFileDialog(`Untitled.${format}`);
      if (path) {
        await this.mainService.api.createNewFile(path, format);
      }
    }
  }

  async openRecentFile(path: string) {
    if (this.mainService.api.openedResourcePath$.getValue() === path) {
      return;
    }
    await this.mainService.api.openFile(path, true);
  }

  getFileName(path: string): string {
    if (!path) return '';
    const lastSlash = Math.max(path.lastIndexOf('/'), path.lastIndexOf('\\'));
    if (lastSlash === -1) return path;
    return path.substring(lastSlash + 1);
  }

  closeFile() {
    this.mainService.api.closeFile().then();
    this.changes.clear();
  }

  async saveResource() {
    try {
      await this.mainService.saveResource();
      this.snackBar.open('File Saved!', 'OK', { duration: 1500 });
    } catch (err: any) {
      this.snackBar.open('Error while saving file! ' + err.errorText, 'OK :(', { duration: 5000 });
    }
  }

  undo() {
    this.changes.undo().then();
  }

  redo() {
    this.changes.redo().then();
  }

  toggleUnknownsVisibility() {
    this.mainService.hideHiddenFields$.next(!this.mainService.hideHiddenFields$.getValue());
  }

  async reloadResource() {
    if (this.changes.hasUnsavedChanges$.value) {
      let dialogRef = this.dialog.open(ConfirmDialogComponent, {
        data: { text: 'There are unsaved changes, which will be lost. Are you sure you want to reload file?' },
      });
      if (!(await firstValueFrom(dialogRef.afterClosed()))) {
        return;
      }
    }
    await this.mainService.reloadResource();
    this.cdr.markForCheck();
  }

  openHomePage() {
    window.open('https://github.com/AndyGura/nfs-resources-converter', '_blank');
  }

  openDocs() {
    window.open('https://github.com/AndyGura/nfs-resources-converter/blob/main/resources/README.md', '_blank');
  }

  openBmac() {
    window.open('https://www.buymeacoffee.com/andygura', '_blank');
  }

  formatChange(change: ChangeEntry): string {
    let renderId = change.id;
    const doubleUnderscoreIndex = renderId.lastIndexOf('__');
    if (doubleUnderscoreIndex !== -1) {
      renderId = renderId.substring(doubleUnderscoreIndex + 2);
    }
    if (change.op === 'set') {
      return `${renderId} = ${change.newValue}`;
    } else if (change.op === 'array_insert') {
      return `${renderId}[${change.index}] = ${change.value}`;
    } else if (change.op === 'array_remove') {
      return `delete ${renderId}[${change.index}]`;
    } else if (change.op === 'array_swap') {
      return `swap elements ${change.indexA} and ${change.indexB} at ${renderId}`;
    } else {
      return `${renderId} (unknown operation)`;
    }
  }

  openConverter() {
    this.dialog.open(ConverterComponent, {
      width: '800px',
      height: '600px',
      disableClose: true,
    });
  }

  openConfig() {
    this.dialog.open(ConfigComponent, {
      width: '600px',
      maxWidth: '90vw',
      maxHeight: '90vh',
      disableClose: true,
    });
  }
}
