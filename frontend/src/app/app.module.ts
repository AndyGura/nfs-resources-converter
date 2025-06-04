import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { EelDelegateService } from './services/eel-delegate.service';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatDividerModule } from '@angular/material/divider';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBarModule } from '@angular/material/snack-bar';
import { MatMenuModule } from '@angular/material/menu';
import { NgxDeepEqualsPureService } from 'ngx-deep-equals-pure';
import { ConfirmDialogComponent } from './components/confirm.dialog/confirm.dialog.component';
import { MatDialogModule } from '@angular/material/dialog';
import { RunCustomActionDialogComponent } from './components/run-custom-action.dialog/run-custom-action.dialog.component';
import { MAT_COLOR_FORMATS, NGX_MAT_COLOR_FORMATS } from '@angular-material-components/color-picker';
import { NavigationBarComponent } from './components/navigation-bar/navigation-bar.component';
import { EditorModule } from './components/editor/editor.module';
import { NavigationBarModule } from './components/navigation-bar/navigation-bar.module';
import { ReactiveFormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { LandingPageComponent } from './components/landing-page/landing-page.component';
import { ConverterComponent } from './components/converter/converter.component';

@NgModule({
  declarations: [AppComponent, ConfirmDialogComponent, RunCustomActionDialogComponent, LandingPageComponent],
  imports: [
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
    MatFormFieldModule,
    MatInputModule,
    MatProgressBarModule,
    ReactiveFormsModule,
    NavigationBarComponent,
    EditorModule,
    NavigationBarModule,
    ConverterComponent,
  ],
  providers: [
    EelDelegateService,
    NgxDeepEqualsPureService,
    { provide: MAT_COLOR_FORMATS, useValue: NGX_MAT_COLOR_FORMATS },
  ],
  bootstrap: [AppComponent],
})
export class AppModule {}
