import { ChangeDetectionStrategy, Component, OnChanges, SimpleChanges } from '@angular/core';
import { GuiComponent } from '../../gui.component';
import { joinId } from '../../../../utils/join-id';
import { BlockSchema, Resource } from '../../types';

@Component({
  selector: 'app-soundbank-block-ui',
  templateUrl: './soundbank.block-ui.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  standalone: false,
})
export class SoundbankBlockUiComponent extends GuiComponent implements OnChanges {
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
