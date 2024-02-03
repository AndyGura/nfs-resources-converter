import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { GuiComponentInterface } from '../../gui-component.interface';
import { joinId } from '../../../../utils/join-id';

@Component({
  selector: 'app-wwww-block-ui',
  templateUrl: './wwww.block-ui.component.html',
  styleUrls: ['./wwww.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class WwwwBlockUiComponent implements GuiComponentInterface {
  private _resource: Resource | null = null;
  get resource(): Resource | null {
    return this._resource;
  }

  @Input()
  set resource(value: Resource | null) {
    this._resource = value;
    this.resourceMap = {};
    console.log(this._resource);
    const childSchema = (this._resource?.schema.fields || []).find(
      (x: { name: string; schema: BlockSchema }) => x.name === 'children',
    )?.schema.child_schema;
    if (!childSchema) return;
    for (let i = 0; i < this.resourceData!.children.length; i++) {
      this.resourceMap[i.toString()] = {
        id: joinId(this._resource!.id, `children/${i}`),
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
