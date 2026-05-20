import { ChangeDetectionStrategy, ChangeDetectorRef, Component, EventEmitter, Input, Output } from '@angular/core';
import { GuiComponentInterface } from '../../gui-component.interface';
import { joinId } from '../../../../utils/join-id';
import { MainService } from '../../../../services/main.service';
import { blockClassStr } from '../../../../utils/block_class_str';
import { NavigationService } from '../../../../services/navigation.service';
import { BlockData, BlockSchema } from '../../types';

type DelegateBlockData = { choice_index: number; data: BlockData };

@Component({
  selector: 'app-delegate-block-ui',
  templateUrl: './delegate.block-ui.component.html',
  styleUrls: ['./delegate.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DelegateBlockUiComponent implements GuiComponentInterface {
  @Input() resourceId?: string;
  @Input() resourceName?: string;
  @Input() resourceSchema?: BlockSchema;
  @Input() resourceData?: { choice_index: number; data: BlockData };
  @Input() resourceDescription?: string;

  @Input() hideName?: boolean;
  @Input() hideBlockActions?: boolean;
  @Input() disabled?: boolean;

  // choiceDataCaches: BlockData[] = [];

  constructor(readonly main: MainService, readonly navigation: NavigationService, readonly cdr: ChangeDetectorRef) {}

  // setChoiceIndex(newIndex: number): void {
  // if (this._resource) {
  //   this.choiceDataCaches[this._resource.data.choice_index] = this.childResource!.data;
  //   this._resource.data.choice_index = newIndex;
  //   this._resource.data.data = this.choiceDataCaches[newIndex];
  //   this.updateChild();
  //   this.changed.emit();
  // }
  // }

  @Output('changed') changed: EventEmitter<void> = new EventEmitter<void>();
  protected readonly blockClassStr = blockClassStr;
  protected readonly joinId = joinId;
}
