import { Component, EventEmitter, Input, Output } from '@angular/core';
import { ViewMode, ViewModeController } from './view-mode.controller';

@Component({
  selector: 'app-view-mode-toolbar',
  templateUrl: './view-mode-toolbar.component.html',
  styleUrls: ['./view-mode-toolbar.component.scss']
})
export class ViewModeToolbarComponent {
  @Input() viewModeController?: ViewModeController;
  @Input() currentViewMode: ViewMode = 'material';
  @Output() viewModeChanged = new EventEmitter<ViewMode>();

  setViewMode(mode: ViewMode): void {
    this.viewModeChanged.emit(mode);
  }

  frameAll(): void {
    this.viewModeController?.frameAll();
  }
}
