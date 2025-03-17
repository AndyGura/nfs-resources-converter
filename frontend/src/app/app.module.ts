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
import { NumberBlockUiComponent } from './components/editor/library/number.block-ui/number.block-ui.component';
import { ArrayBlockUiComponent } from './components/editor/library/array.block-ui/array.block-ui.component';
import { BitmapBlockUiComponent } from './components/editor/eac/bitmap.block-ui/bitmap.block-ui.component';
import { PaletteBlockUiComponent } from './components/editor/eac/palette.block-ui/palette.block-ui.component';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBarModule } from '@angular/material/snack-bar';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { BinaryBlockUiComponent } from './components/editor/library/binary.block-ui/binary.block-ui.component';
import { MatPaginatorModule } from '@angular/material/paginator';
import { AngleBlockUiComponent } from './components/editor/eac/angle.block-ui/angle.block-ui.component';
import { SidenavResListComponent } from './components/editor/common/sidenav-res-list/sidenav-res-list.component';
import { MatListModule } from '@angular/material/list';
import { WwwwBlockUiComponent } from './components/editor/eac/wwww.block-ui/wwww.block-ui.component';
import { MatCardModule } from '@angular/material/card';
import { NgxDeepEqualsPureService } from 'ngx-deep-equals-pure';
import { EnumBlockUiComponent } from './components/editor/library/enum.block-ui/enum.block-ui.component';
import { MatSelectModule } from '@angular/material/select';
import { FlagsBlockUiComponent } from './components/editor/library/flags.block-ui/flags.block-ui.component';
import { ConfirmDialogComponent } from './components/confirm.dialog/confirm.dialog.component';
import { MatDialogModule } from '@angular/material/dialog';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatMenuModule } from '@angular/material/menu';
import { TriMapBlockUiComponent } from './components/editor/eac/tri-map.block-ui/tri-map.block-ui.component';
import { TrkMapBlockUiComponent } from './components/editor/eac/trk-map.block-ui/trk-map.block-ui.component';
import { RunCustomActionDialogComponent } from './components/run-custom-action.dialog/run-custom-action.dialog.component';
import { OripGeometryBlockUiComponent } from './components/editor/eac/orip-geometry.block-ui/orip-geometry.block-ui.component';
import { MinimapComponent } from './components/editor/common/minimap/minimap.component';
import { DelegateBlockUiComponent } from './components/editor/library/delegate.block-ui/delegate.block-ui.component';
import { MatOptionModule } from '@angular/material/core';
import { FenceTypeBlockUiComponent } from './components/editor/eac/fence-type.block-ui/fence-type.block-ui.component';
import { BlockActionsComponent } from './components/editor/common/block-actions/block-actions.component';
import { SoundbankBlockUiComponent } from './components/editor/eac/soundbank.block-ui/soundbank.block-ui.component';
import { EacsAudioBlockUiComponent } from './components/editor/eac/eacs-audio.block-ui/eacs-audio.block-ui.component';
import { GeoGeometryBlockUiComponent } from './components/editor/eac/geo-geometry.block-ui/geo-geometry.block-ui.component';
import { ObjViewerComponent } from './components/editor/common/obj-viewer/obj-viewer.component';
import { BaseArchiveBlockUiComponent } from './components/editor/eac/base-archive.block-ui/base-archive.block-ui.component';
import {
  MAT_COLOR_FORMATS,
  NGX_MAT_COLOR_FORMATS,
  NgxMatColorPickerModule,
} from '@angular-material-components/color-picker';
import { HexEditorModule } from 'ngx-hex-editor';
import { SkipBlockUiComponent } from './components/editor/library/skip.block-ui/skip.block-ui.component';

@NgModule({
  declarations: [
    AppComponent,
    EditorComponent,
    FallbackBlockUiComponent,
    DataBlockUIDirective,
    CompoundBlockUiComponent,
    StringBlockUiComponent,
    NumberBlockUiComponent,
    ArrayBlockUiComponent,
    BitmapBlockUiComponent,
    PaletteBlockUiComponent,
    BinaryBlockUiComponent,
    AngleBlockUiComponent,
    SidenavResListComponent,
    BaseArchiveBlockUiComponent,
    WwwwBlockUiComponent,
    EnumBlockUiComponent,
    FlagsBlockUiComponent,
    ConfirmDialogComponent,
    TriMapBlockUiComponent,
    TrkMapBlockUiComponent,
    RunCustomActionDialogComponent,
    OripGeometryBlockUiComponent,
    MinimapComponent,
    DelegateBlockUiComponent,
    FenceTypeBlockUiComponent,
    BlockActionsComponent,
    SoundbankBlockUiComponent,
    EacsAudioBlockUiComponent,
    GeoGeometryBlockUiComponent,
    ObjViewerComponent,
    SkipBlockUiComponent,
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
    MatPaginatorModule,
    MatListModule,
    MatCardModule,
    MatSelectModule,
    MatDialogModule,
    MatProgressSpinnerModule,
    MatMenuModule,
    ReactiveFormsModule,
    MatOptionModule,
    NgxMatColorPickerModule,
    HexEditorModule,
  ],
  providers: [
    EelDelegateService,
    NgxDeepEqualsPureService,
    { provide: MAT_COLOR_FORMATS, useValue: NGX_MAT_COLOR_FORMATS },
  ],
  bootstrap: [AppComponent],
})
export class AppModule {}
