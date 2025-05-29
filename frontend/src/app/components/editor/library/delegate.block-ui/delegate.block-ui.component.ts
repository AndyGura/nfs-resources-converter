import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { GuiComponentInterface } from '../../gui-component.interface';
import { joinId } from '../../../../utils/join-id';
import { MainService } from '../../../../services/main.service';
import { blockClassStr } from '../../../../utils/block_class_str';
import { NavigationService } from '../../../../services/navigation.service';

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
    this.updateChild();
  }

  @Input() resourceDescription: string = '';

  @Input() hideBlockActions: boolean = false;

  @Input() disabled: boolean = false;

  childResource: Resource | null = null;
  choiceDataCaches: BlockData[] = [];

  get resourceData(): DelegateBlockData | null {
    return this._resource?.data || null;
  }

  constructor(readonly main: MainService, readonly navigation: NavigationService) {}

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
        id: joinId(this._resource.id, 'data'),
        data: this.choiceDataCaches[this._resource.data.choice_index],
        name: '', // name is displayed in this block, no need to duplicate
        schema: this._resource.schema.possible_resource_schemas[this._resource.data.choice_index],
      };
    }
  }

  @Output('changed') changed: EventEmitter<void> = new EventEmitter<void>();
  protected readonly blockClassStr = blockClassStr;
}
