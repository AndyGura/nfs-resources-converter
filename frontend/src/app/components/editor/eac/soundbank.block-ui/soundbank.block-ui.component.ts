import { ChangeDetectionStrategy, Component, OnChanges, SimpleChanges } from '@angular/core';
import { GuiComponent } from '../../gui.component';
import { joinId } from '../../../../utils/join-id';
import { BlockSchema, Resource } from '../../types';

// TNFS collision bank (SIMDATA/SOUNDBNK/COL*.BNK) samples, as the game uses them (decoded by tnfs-1995)
const COLLISION_BANK_SAMPLES: { [index: number]: string } = {
  0x21: 'light hit / prop',
  0x22: 'medium hit',
  0x23: 'fence hit',
  0x24: 'heavy hit',
  0x25: 'landing / bump',
  0x26: 'gravel squeal loop',
  0x27: 'body scrape loop',
  0x28: 'gravel squeal loop',
  0x29: 'wind loop',
  0x2a: 'tyre squeal loop',
  0x2b: 'tyre squeal loop',
  0x2d: 'tyre squeal loop',
  0x2e: 'gravel squeal loop',
  0x34: 'body scrape loop',
  0x36: 'body scrape loop',
  0x38: 'tyre squeal loop',
  0x3a: 'tyre squeal loop',
  0x3e: 'waterfall loop',
};

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
      // children are in file order, which is not always the index order of items_descr: sort indices by offset
      const idxs = (this.resourceData!.items_descr as number[])
        .map((x, i) => [x, i])
        .filter(([x, i]) => x > 0)
        .sort((a, b) => a[0] - b[0])
        .map(([x, i]) => i);
      const isCollisionBank = /(^|[\\/])COL[^\\/]*\.BNK$/i.test(this.resourceId || '');
      for (let i = 0; i < this.resourceData!.children.length; i++) {
        const meaning = isCollisionBank ? COLLISION_BANK_SAMPLES[idxs[i]] : undefined;
        this.resourceMap['0x' + idxs[i].toString(16) + (meaning ? ` (${meaning})` : '')] = {
          id: joinId(this.resourceId || '', `children/${i}`),
          data: this.resourceData!.children[i],
          schema: childSchema,
          name: '',
        };
      }
    }
  }
}
