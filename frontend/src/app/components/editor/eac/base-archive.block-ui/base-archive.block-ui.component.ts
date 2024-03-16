import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { GuiComponentInterface } from '../../gui-component.interface';
import { joinId } from '../../../../utils/join-id';

@Component({
  selector: 'app-base-archive-block-ui',
  templateUrl: './base-archive.block-ui.component.html',
  styleUrls: ['./base-archive.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BaseArchiveBlockUiComponent implements GuiComponentInterface {
  private _resource: Resource | null = null;
  get resource(): Resource | null {
    return this._resource;
  }

  @Input()
  set resource(value: Resource | null) {
    this._resource = value;
    this.resourceMap = {};
    const childSchema = (this._resource?.schema.fields || []).find(
      (x: { name: string; schema: BlockSchema }) => x.name === 'children',
    )?.schema.child_schema;
    if (!childSchema) return;
    let unaliasedCounter = 0;
    for (const [i, alias] of this.resourceData!.children_aliases.entries()) {
      let childName = alias || '__' + unaliasedCounter++;
      this.resourceMap[childName] = {
        id: joinId(this._resource?.id || '', `children/${i}`),
        data: this.resourceData?.children[i],
        schema: childSchema,
        name: '',
      };
    }
  }

  get resourceData(): BlockData | null {
    return this._resource?.data;
  }

  @Input() hideBlockActions: boolean = false;

  resourceMap: { [key: string]: Resource } = {};

  @Output('changed') changed: EventEmitter<void> = new EventEmitter<void>();
}
