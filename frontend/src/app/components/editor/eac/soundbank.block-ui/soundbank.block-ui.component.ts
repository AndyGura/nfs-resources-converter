import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { GuiComponentInterface } from '../../gui-component.interface';
import { joinId } from '../../../../utils/join-id';
import { BlockData, BlockSchema, Resource } from '../../types';

@Component({
  selector: 'app-soundbank-block-ui',
  templateUrl: './soundbank.block-ui.component.html',
  styleUrls: ['./soundbank.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SoundbankBlockUiComponent implements GuiComponentInterface {
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
    let idxs = (this.resourceData!.items_descr as number[])
      .map((x, i) => [x, i])
      .filter(([x, i]) => x > 0)
      .map(([x, i]) => i);
    for (let i = 0; i < this.resourceData!.children.length; i++) {
      this.resourceMap['0x' + idxs[i].toString(16)] = {
        id: joinId(this._resource?.id || '', `children/${i}`),
        data: this.resourceData!.children[i],
        schema: childSchema,
        name: '',
      };
    }
  }

  get resourceData(): BlockData | null {
    return this._resource?.data;
  }

  resourceMap: { [key: string]: Resource } = {};

  @Output('changed') changed: EventEmitter<void> = new EventEmitter<void>();
}
