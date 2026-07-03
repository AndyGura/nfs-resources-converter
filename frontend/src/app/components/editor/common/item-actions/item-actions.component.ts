import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';

@Component({
  selector: 'app-item-actions',
  templateUrl: './item-actions.component.html',
  styleUrls: ['./item-actions.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  standalone: false,
})
export class ItemActionsComponent {
  @Input() index: number = 0;
  @Input() totalItems: number = 0;
  @Input() showRemove: boolean = true;
  @Input() disabled: boolean = false;

  @Output() moveUp = new EventEmitter<number>();
  @Output() moveDown = new EventEmitter<number>();
  @Output() remove = new EventEmitter<number>();
}
