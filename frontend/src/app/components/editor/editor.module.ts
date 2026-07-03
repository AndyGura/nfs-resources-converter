import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { EditorComponent } from './editor.component';
import { DataBlockUIDirective } from './data-block-ui.directive';
import { CompoundBlockUiComponent } from './library/compound.block-ui/compound.block-ui.component';
import { NumberBlockUiComponent } from './library/number.block-ui/number.block-ui.component';
import { StringBlockUiComponent } from './library/string.block-ui/string.block-ui.component';
import { ArrayBlockUiComponent } from './library/array.block-ui/array.block-ui.component';
import { DataTableComponent } from './common/data-table/data-table.component';
import { ItemActionsComponent } from './common/item-actions/item-actions.component';
import { BinaryBlockUiComponent } from './library/binary.block-ui/binary.block-ui.component';
import { EnumBlockUiComponent } from './library/enum.block-ui/enum.block-ui.component';
import { SubByteCompoundBlockUiComponent } from './library/sub-byte-compound.block-ui/sub-byte-compound.block-ui.component';
import { DelegateBlockUiComponent } from './library/delegate.block-ui/delegate.block-ui.component';
import { AngleBlockUiComponent } from './eac/angle.block-ui/angle.block-ui.component';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatDividerModule } from '@angular/material/divider';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatSelectModule } from '@angular/material/select';
import { MatPaginatorModule } from '@angular/material/paginator';
import { MatListModule } from '@angular/material/list';
import { MatCardModule } from '@angular/material/card';
import { MatDialogModule } from '@angular/material/dialog';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatMenuModule } from '@angular/material/menu';
import { MatOptionModule } from '@angular/material/core';
import { HexEditorComponent } from 'ngx-hex-editor';
import { SidenavResListComponent } from './common/sidenav-res-list/sidenav-res-list.component';
import { MinimapComponent } from './common/minimap/minimap.component';
import { BlockActionsComponent } from './common/block-actions/block-actions.component';
import { ObjViewerComponent } from './common/obj-viewer/obj-viewer.component';
import { ViewModeToolbarComponent } from './common/obj-viewer/view-mode-toolbar/view-mode-toolbar.component';

import { MatSliderModule } from '@angular/material/slider';
import { BaseArchiveBlockUiComponent } from './eac/base-archive.block-ui/base-archive.block-ui.component';
import { ImageBlockUiComponent } from './eac/image.block-ui/image.block-ui.component';
import { PaletteBlockUiComponent } from './eac/palette.block-ui/palette.block-ui.component';
import { OripGeometryBlockUiComponent } from './eac/orip-geometry.block-ui/orip-geometry.block-ui.component';
import { EacsAudioBlockUiComponent } from './eac/eacs-audio.block-ui/eacs-audio.block-ui.component';
import { SoundbankBlockUiComponent } from './eac/soundbank.block-ui/soundbank.block-ui.component';
import { TriMapBlockUiComponent } from './eac/tri-map.block-ui/tri-map.block-ui.component';
import { TrkMapBlockUiComponent } from './eac/trk-map.block-ui/trk-map.block-ui.component';
import { GeoGeometryBlockUiComponent } from './eac/geo-geometry.block-ui/geo-geometry.block-ui.component';
import { FrdMapBlockUiComponent } from './eac/frd-map.block-ui/frd-map.block-ui.component';
import { CrpGeometryBlockUiComponent } from './eac/crp-geometry.block-ui/crp-geometry.block-ui.component';
import { FontBlockUiComponent } from './eac/font.block-ui/font.block-ui.component';
import { MatTab, MatTabGroup } from '@angular/material/tabs';

@NgModule({
  declarations: [
    EditorComponent,
    DataBlockUIDirective,
    DataTableComponent,
    ItemActionsComponent,
    SidenavResListComponent,
    MinimapComponent,
    BlockActionsComponent,
    ObjViewerComponent,
    ViewModeToolbarComponent,

    // common data blocks
    NumberBlockUiComponent,
    StringBlockUiComponent,
    EnumBlockUiComponent,
    BinaryBlockUiComponent,
    ArrayBlockUiComponent,
    CompoundBlockUiComponent,
    SubByteCompoundBlockUiComponent,
    DelegateBlockUiComponent,
    AngleBlockUiComponent,

    // common nfs data blocks
    BaseArchiveBlockUiComponent,
    ImageBlockUiComponent,
    PaletteBlockUiComponent,
    FontBlockUiComponent,

    // specific data blocks
    OripGeometryBlockUiComponent,
    EacsAudioBlockUiComponent,
    SoundbankBlockUiComponent,
    TriMapBlockUiComponent,
    GeoGeometryBlockUiComponent,
    TrkMapBlockUiComponent,
    FrdMapBlockUiComponent,
    CrpGeometryBlockUiComponent,
  ],
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MatExpansionModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    MatDividerModule,
    MatTooltipModule,
    MatSelectModule,
    MatPaginatorModule,
    MatListModule,
    MatCardModule,
    MatDialogModule,
    MatProgressSpinnerModule,
    MatMenuModule,
    MatOptionModule,
    MatCheckboxModule,
    MatSliderModule,
    HexEditorComponent,
    MatTab,
    MatTabGroup,
  ],
  exports: [EditorComponent, SidenavResListComponent, BlockActionsComponent],
})
export class EditorModule {}
