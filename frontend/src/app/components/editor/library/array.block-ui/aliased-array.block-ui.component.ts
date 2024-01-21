import {ChangeDetectionStrategy, Component} from '@angular/core';
import {ArrayBlockUiComponent} from './array.block-ui.component';

@Component({
  selector: 'app-aliased-array-block-ui',
  templateUrl: './array.block-ui.component.html',
  styleUrls: ['./array.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AliasedArrayBlockUiComponent extends ArrayBlockUiComponent {
  protected override buildChildren(): void {
    this.children = (this.resourceData || []).map((d: BlockData, i: number) => ({
      id: this.resource!.id + (this.resource!.id.includes('__') ? '/' : '__') + i,
      name: d.name,
      data: d.data,
      schema: this.resource!.schema.child_schema,
    }));
  }
}
