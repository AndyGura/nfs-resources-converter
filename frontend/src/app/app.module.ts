import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { BrowserModule } from '@angular/platform-browser';
import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { ApiDelegateService } from './services/api/api-delegate.service';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatDividerModule } from '@angular/material/divider';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBarModule } from '@angular/material/snack-bar';
import { MatMenuModule } from '@angular/material/menu';
import { MatSelectModule } from '@angular/material/select';
import { MatListModule } from '@angular/material/list';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { ConfirmDialogComponent } from './components/confirm.dialog/confirm.dialog.component';
import { MatDialogModule } from '@angular/material/dialog';
import { RunCustomActionDialogComponent } from './components/run-custom-action.dialog/run-custom-action.dialog.component';
import { ErrorDialogComponent } from './components/error.dialog/error.dialog.component';
import { NavigationBarComponent } from './components/navigation-bar/navigation-bar.component';
import { EditorModule } from './components/editor/editor.module';
import { NavigationBarModule } from './components/navigation-bar/navigation-bar.module';
import { ReactiveFormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { LandingPageComponent } from './components/landing-page/landing-page.component';
import { ConverterComponent } from './components/converter/converter.component';
import { ConfigComponent } from './components/config/config.component';
import { NewFileDialogComponent } from './components/new-file.dialog/new-file.dialog.component';

@NgModule({
  declarations: [
    AppComponent,
    ConfirmDialogComponent,
    RunCustomActionDialogComponent,
    ErrorDialogComponent,
    LandingPageComponent,
    NewFileDialogComponent,
  ],
  imports: [
    CommonModule,
    BrowserModule,
    AppRoutingModule,
    BrowserAnimationsModule,
    MatToolbarModule,
    MatSnackBarModule,
    MatDividerModule,
    MatTooltipModule,
    MatButtonModule,
    MatIconModule,
    MatDialogModule,
    MatMenuModule,
    MatSelectModule,
    MatListModule,
    MatCheckboxModule,
    MatFormFieldModule,
    MatInputModule,
    MatProgressBarModule,
    MatProgressSpinnerModule,
    ReactiveFormsModule,
    NavigationBarComponent,
    EditorModule,
    NavigationBarModule,
    ConverterComponent,
    ConfigComponent,
  ],
  providers: [ApiDelegateService],
  bootstrap: [AppComponent],
})
export class AppModule {}
