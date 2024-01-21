import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { GuiComponentInterface } from '../../gui-component.interface';

type DelegateBlockData = { choice_index: number; data: BlockData };

@Component({
  selector: 'app-delegate.block-ui',
  templateUrl: './delegate.block-ui.component.html',
  styleUrls: ['./delegate.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DelegateBlockUiComponent implements GuiComponentInterface {
  private _resource: Resource<DelegateBlockData> | null = null;

  public get resource(): Resource<DelegateBlockData> | null {
    return this._resource;
  }

  @Input()
  set resource(value: Resource<DelegateBlockData> | null) {
    const isNewResource = !this._resource || !value || this._resource.id !== value.id;
    this._resource = value;
    if (isNewResource) {
      this.choiceDataCaches = new Array(this._resource?.schema.possible_resource_schemas || 0).fill(null);
      if (this._resource) {
        this.choiceDataCaches[this._resource.data.choice_index] = this._resource.data.data;
      }
    }
    if (!this._resource) {
      this.choiceResource = null;
    } else {
      this.choiceResource = {
        id: this._resource.id + '/' + 'choice_index',
        name: 'Block type choice',
        data: this._resource.data.choice_index,
        schema: {
          block_class_mro: 'EnumBlock__IntegerBlock__DataBlock',
          choices: [
            // TODO finish EnumBlock and use another <app-editor here for correct file changes delta flow
          ],
        },
      };
    }
    this.updateChild();
  }

  choiceResource: Resource | null = null;
  childResource: Resource | null = null;
  choiceDataCaches: BlockData[] = [];

  get resourceData(): DelegateBlockData | null {
    return this._resource?.data || null;
  }

  setChoiceIndex(newIndex: number): void {
    if (this._resource) {
      this.choiceDataCaches[this._resource.data.choice_index] = this.childResource!.data;
      this._resource.data.choice_index = newIndex;
      this._resource.data.data = this.choiceDataCaches[newIndex];
      this.updateChild();
      this.changed.emit();
    }
  }

  updateChild(): void {
    if (!this._resource) {
      this.childResource = null;
    } else {
      this.childResource = {
        ...this._resource,
        id: this._resource.id + (this._resource.id.includes('__') ? '/' : '__') + 'data',
        data: this.choiceDataCaches[this._resource.data.choice_index],
        schema: this._resource.schema.possible_resource_schemas[this._resource.data.choice_index],
      };
    }
  }

  @Output('changed') changed: EventEmitter<void> = new EventEmitter<void>();
}
