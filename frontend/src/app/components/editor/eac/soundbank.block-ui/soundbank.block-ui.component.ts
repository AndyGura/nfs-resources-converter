import {
  ChangeDetectionStrategy,
  Component,
  EventEmitter,
  Input,
  OnChanges,
  Output,
  SimpleChanges,
} from '@angular/core';
import { GuiComponentInterface } from '../../gui-component.interface';
import { joinId } from '../../../../utils/join-id';
import { BlockData, BlockSchema, Resource } from '../../types';

@Component({
  selector: 'app-soundbank-block-ui',
  templateUrl: './soundbank.block-ui.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SoundbankBlockUiComponent implements GuiComponentInterface, OnChanges {
  @Input() resourceId?: string;
  @Input() resourceName?: string;
  @Input() resourceSchema?: BlockSchema;
  @Input() resourceData?: BlockData;
  @Input() resourceDescription?: string;

  @Input() hideName?: boolean;
  @Input() hideBlockActions?: boolean;
  @Input() disabled?: boolean;

  @Output('changed') changed: EventEmitter<void> = new EventEmitter<void>();

  resourceMap: { [key: string]: Resource } = {};

  ngOnChanges(changes: SimpleChanges): void {
    if (
      changes.hasOwnProperty('resourceId') ||
      changes.hasOwnProperty('resourceData') ||
      changes.hasOwnProperty('resourceSchema')
    ) {
      this.resourceMap = {};
      const childSchema = (this.resourceSchema.fields || []).find(
        (x: { name: string; schema: BlockSchema }) => x.name === 'children',
      )?.schema.child_schema;
      if (!childSchema) return;
      let idxs = (this.resourceData!.items_descr as number[])
        .map((x, i) => [x, i])
        .filter(([x, i]) => x > 0)
        .map(([x, i]) => i);
      for (let i = 0; i < this.resourceData!.children.length; i++) {
        this.resourceMap['0x' + idxs[i].toString(16)] = {
          id: joinId(this.resourceId || '', `children/${i}`),
          data: this.resourceData!.children[i],
          schema: childSchema,
          name: '',
        };
      }
    }
  }
}
