import { ChangeDetectionStrategy, Component, Input } from '@angular/core';
import { SubscribableGuiComponent } from '../../gui.component';
import { joinId } from '../../../../utils/join-id';
import { BlockData, BlockSchema, Resource } from '../../types';

@Component({
  selector: 'app-base-archive-block-ui',
  templateUrl: './base-archive.block-ui.component.html',
  styleUrls: ['./base-archive.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  standalone: false,
})
export class BaseArchiveBlockUiComponent extends SubscribableGuiComponent {
  override get resourceSchema(): BlockSchema {
    return super.resourceSchema;
  }

  @Input()
  override set resourceSchema(value: BlockSchema) {
    super.resourceSchema = value;
    this.buildResourceMap();
  }

  override get resourceData(): BlockData {
    return super.resourceData;
  }

  @Input()
  override set resourceData(value: BlockData) {
    super.resourceData = value;
    this.buildResourceMap();
  }

  override onExternalChanges() {
    super.onExternalChanges();
    this.buildResourceMap();
  }

  resourceMap: { [key: string]: Resource } = {};

  buildResourceMap() {
    this.resourceMap = {};
    if (!this._resourceSchema || !this._resourceData) return;
    const childSchema = this._resourceSchema.fields.find(
      (x: { name: string; schema: BlockSchema }) => x.name === 'children',
    )?.schema.child_schema;
    if (!childSchema) return;
    let unaliasedCounter = 0;
    for (const [i, alias] of this._resourceData.children_aliases.entries()) {
      let childName = alias || '__' + unaliasedCounter++;
      this.resourceMap[childName] = {
        id: joinId(this.resourceId || '', `children/${i}/data`),
        data: this._resourceData.children[i].data,
        schema: childSchema.possible_resource_schemas[this._resourceData.children[i].choice_index],
        name: '',
      };
    }
    this.cdr.markForCheck();
  }
}
