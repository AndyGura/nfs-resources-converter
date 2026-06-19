import { Component, EventEmitter, Input, Output, ChangeDetectionStrategy } from '@angular/core';
import { ViewMode, ViewModeController } from './view-mode.controller';

@Component({
  selector: 'app-view-mode-toolbar',
  templateUrl: './view-mode-toolbar.component.html',
  styleUrls: ['./view-mode-toolbar.component.scss'],
  changeDetection: ChangeDetectionStrategy.Eager,
  standalone: false,
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
