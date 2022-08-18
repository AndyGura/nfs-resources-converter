import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';

import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { EelDelegateService } from './services/eel-delegate.service';
import { EditorComponent } from './components/editor/editor.component';
import { FallbackBlockUiComponent } from './components/editor/fallback.block-ui/fallback.block-ui.component';
import { DataBlockUIDirective } from './components/editor/data-block-ui.directive';

@NgModule({
  declarations: [
    AppComponent,
    EditorComponent,
    FallbackBlockUiComponent,
    DataBlockUIDirective
  ],
  imports: [
    BrowserModule,
    AppRoutingModule,
  ],
  providers: [EelDelegateService],
  bootstrap: [AppComponent]
})
export class AppModule {
}
