import { ChangeDetectionStrategy, Component } from '@angular/core';
import { SubscribableGuiComponent } from '../../gui.component';
import { joinId } from '../../../../utils/join-id';
import { BlockData, BlockSchema, CustomAction } from '../../types';
import { blockClassStr } from '../../../../utils/block_class_str';

type DelegateBlockData = { choice_index: number; data: BlockData };

@Component({
  selector: 'app-delegate-block-ui',
  templateUrl: './delegate.block-ui.component.html',
  styleUrls: ['./delegate.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  standalone: false,
})
export class DelegateBlockUiComponent extends SubscribableGuiComponent<DelegateBlockData> {
  // choiceDataCaches: BlockData[] = [];

  // setChoiceIndex(newIndex: number): void {
  // if (this._resource) {
  //   this.choiceDataCaches[this._resource.data.choice_index] = this.childResource!.data;
  //   this._resource.data.choice_index = newIndex;
  //   this._resource.data.data = this.choiceDataCaches[newIndex];
  //   this.updateChild();
  //   this.changed.emit();
  // }
  // }

  getChildSchema(): BlockSchema | undefined {
    if (!this.resourceData || !this.resourceData) return undefined;
    let schema = structuredClone(this.resourceSchema.possible_resource_schemas[this.resourceData.choice_index]);
    if (this.resourceSchema.custom_actions?.length) {
      schema.custom_actions = [
        ...schema.custom_actions,
        ...this.resourceSchema.custom_actions.map((a: CustomAction) => ({
          ...a,
          idDepth: a.idDepth ? a.idDepth + 1 : 1,
        })),
      ];
    }
    return schema;
  }

  protected readonly joinId = joinId;
  protected readonly blockClassStr = blockClassStr;
}
