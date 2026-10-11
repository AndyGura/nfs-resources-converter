import { ChangeDetectionStrategy, Component, OnChanges, SimpleChanges } from '@angular/core';
import { GuiComponent } from '../../gui.component';
import { joinId } from '../../../../utils/join-id';
import { BlockSchema, Resource } from '../../types';

// TNFS race sound bank samples, as the game uses them (decoded by tnfs-1995). All banks of a race (car *SW, opponent
// O*MB*, collision COL*, NFS_FMMB) share one sample id table, so an id means the same in every one of them
const RACE_BANK_SAMPLES: { [index: number]: string } = {
  0x03: 'horn',
  0x20: 'gear click',
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
  0x3d: 'left waterfall loop, Win95 SE',
  0x3e: 'waterfall loop',
  0x3f: 'traffic horn loop',
  0x41: 'opponent car horn loop',
  0x50: 'cave drips in a tunnel, Win95 SE',
  0x61: 'radar detector beep',
  0x62: 'police siren loop',
  0x64: 'police siren loop in a tunnel',
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
      // the frontend bank is not loaded in a race
      const isRaceBank = !/(^|[\\/])FRONT[^\\/]*\.BNK$/i.test(this.resourceId || '');
      for (let i = 0; i < this.resourceData!.children.length; i++) {
        const meaning = isRaceBank ? RACE_BANK_SAMPLES[idxs[i]] : undefined;
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
