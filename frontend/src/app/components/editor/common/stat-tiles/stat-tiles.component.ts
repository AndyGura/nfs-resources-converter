import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';

export type StatTileEdit = {
  value: number;
  step?: number;
  min?: number;
  max?: number;
  // shown after the input
  unit?: string;
};

export type StatTile = {
  // identifies the tile in `tileChange`, required for editable tiles
  id?: string;
  label: string;
  value: string;
  // smaller second line: another unit, where the value comes from...
  sub?: string;
  hint?: string;
  tone?: 'default' | 'accent' | 'muted' | 'warn';
  // makes the value an input; the host applies the typed value
  edit?: StatTileEdit;
};

// A row of key figures, e.g. a summary on top of a bespoke editor. Tiles with `edit` take a typed value
@Component({
  selector: 'app-stat-tiles',
  templateUrl: './stat-tiles.component.html',
  styleUrls: ['./stat-tiles.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  standalone: false,
})
export class StatTilesComponent {
  @Input() tiles: StatTile[] = [];
  @Input() disabled: boolean | null | undefined = false;

  @Output() tileChange = new EventEmitter<{ id: string; value: number }>();

  onEdit(tile: StatTile, input: HTMLInputElement) {
    const value = parseFloat(input.value);
    if (!tile.id || !tile.edit || !isFinite(value) || value === tile.edit.value) {
      input.value = '' + (tile.edit?.value ?? '');
      return;
    }
    this.tileChange.emit({ id: tile.id, value });
  }

  cancel(tile: StatTile, input: HTMLInputElement) {
    input.value = '' + (tile.edit?.value ?? '');
    input.blur();
  }

  inputWidth(tile: StatTile): number {
    return Math.max(2, ('' + tile.edit!.value).length) + 1;
  }
}
