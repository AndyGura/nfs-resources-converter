import { ChangeDetectionStrategy, ChangeDetectorRef, Component, EventEmitter, Input, Output } from '@angular/core';
import { GuiComponentInterface } from '../../gui-component.interface';
import { joinId } from '../../../../utils/join-id';
import { BlockData, BlockSchema, Resource } from '../../types';

@Component({
  selector: 'app-base-archive-block-ui',
  templateUrl: './base-archive.block-ui.component.html',
  styleUrls: ['./base-archive.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BaseArchiveBlockUiComponent implements GuiComponentInterface {
  @Input() resourceId?: string;
  @Input() resourceName?: string;
  private _resourceSchema?: BlockSchema;
  get resourceSchema(): BlockSchema {
    return this._resourceSchema;
  }

  @Input()
  set resourceSchema(value: BlockSchema) {
    this._resourceSchema = value;
    this.buildResourceMap();
  }

  private _resourceData?: BlockData;
  get resourceData(): BlockData {
    return this._resourceData;
  }

  @Input()
  set resourceData(value: BlockData) {
    this._resourceData = value;
    this.buildResourceMap();
  }

  @Input() resourceDescription?: string;

  @Input() hideName?: boolean;
  @Input() hideBlockActions?: boolean;
  @Input() disabled?: boolean;

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
        id: joinId(this.resourceId || '', `children/${i}`),
        data: this._resourceData.children[i],
        schema: childSchema,
        name: '',
      };
    }
    this.cdr.markForCheck();
  }

  @Output('changed') changed: EventEmitter<void> = new EventEmitter<void>();

  constructor(readonly cdr: ChangeDetectorRef) {}
}
