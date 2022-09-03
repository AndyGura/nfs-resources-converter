import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';

import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { EelDelegateService } from './services/eel-delegate.service';
import { EditorComponent } from './components/editor/editor.component';
import { DataBlockUIDirective } from './components/editor/data-block-ui.directive';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatDividerModule } from '@angular/material/divider';
import { MatTooltipModule } from '@angular/material/tooltip';
import { FallbackBlockUiComponent } from './components/editor/library/fallback.block-ui/fallback.block-ui.component';
import { CompoundBlockUiComponent } from './components/editor/library/compound.block-ui/compound.block-ui.component';
import { StringBlockUiComponent } from './components/editor/library/string.block-ui/string.block-ui.component';
import { IntegerBlockUiComponent } from './components/editor/library/integer.block-ui/integer.block-ui.component';
import { ArrayBlockUiComponent } from './components/editor/library/array.block-ui/array.block-ui.component';
import { BitmapBlockUiComponent } from './components/editor/eac/bitmap.block-ui/bitmap.block-ui.component';
import { PaletteBlockUiComponent } from './components/editor/eac/palette.block-ui/palette.block-ui.component';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBarModule } from '@angular/material/snack-bar';
import { FormsModule } from '@angular/forms';

@NgModule({
  declarations: [
    AppComponent,
    EditorComponent,
    FallbackBlockUiComponent,
    DataBlockUIDirective,
    CompoundBlockUiComponent,
    StringBlockUiComponent,
    IntegerBlockUiComponent,
    ArrayBlockUiComponent,
    BitmapBlockUiComponent,
    PaletteBlockUiComponent,
  ],
  imports: [
    BrowserModule,
    AppRoutingModule,
    BrowserAnimationsModule,
    FormsModule,
    MatToolbarModule,
    MatFormFieldModule,
    MatInputModule,
    MatExpansionModule,
    MatSnackBarModule,
    MatDividerModule,
    MatTooltipModule,
    MatButtonModule,
    MatIconModule,
  ],
  providers: [EelDelegateService],
  bootstrap: [AppComponent]
})
export class AppModule {
}
