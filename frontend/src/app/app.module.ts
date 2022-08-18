import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';

import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { EelDelegateService } from './services/eel-delegate.service';
import { EditorComponent } from './components/editor/editor.component';
import { FallbackBlockUiComponent } from './components/editor/fallback.block-ui/fallback.block-ui.component';
import { DataBlockUIDirective } from './components/editor/data-block-ui.directive';
import { CompoundBlockUiComponent } from './components/editor/compound.block-ui/compound.block-ui.component';
import { StringBlockUiComponent } from './components/editor/string.block-ui/string.block-ui.component';
import { IntegerBlockUiComponent } from './components/editor/integer.block-ui/integer.block-ui.component';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { ArrayBlockUiComponent } from './components/editor/array.block-ui/array.block-ui.component';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatDividerModule } from '@angular/material/divider';
import { MatTooltipModule } from '@angular/material/tooltip';
import { BitmapBlockUiComponent } from './components/editor/bitmap.block-ui/bitmap.block-ui.component';
import { PaletteBlockUiComponent } from './components/editor/palette.block-ui/palette.block-ui.component';

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
    MatToolbarModule,
    MatFormFieldModule,
    MatInputModule,
    MatExpansionModule,
    MatDividerModule,
    MatTooltipModule,
  ],
  providers: [EelDelegateService],
  bootstrap: [AppComponent]
})
export class AppModule {
}
