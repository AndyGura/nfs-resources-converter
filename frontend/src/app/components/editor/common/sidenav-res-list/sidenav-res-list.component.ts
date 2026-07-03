import { ChangeDetectionStrategy, Component, inject, Input } from '@angular/core';
import { NavigationService } from '../../../../services/navigation.service';
import { Resource, ResourceError } from '../../types';
import { joinId } from '../../../../utils/join-id';
import { fileFormatIcon } from '../../../../utils/file-format-icon';
import { SubscribableGuiComponent } from '../../gui.component';

@Component({
  selector: 'app-sidenav-res-list',
  templateUrl: './sidenav-res-list.component.html',
  styleUrls: ['./sidenav-res-list.component.scss'],
  host: { class: 'full-screen-editor' },
  changeDetection: ChangeDetectionStrategy.OnPush,
  standalone: false,
})
export class SidenavResListComponent extends SubscribableGuiComponent {
  _resources: { [key: string]: Resource | ResourceError } = {};
  get resources(): { [key: string]: Resource | ResourceError } {
    return this._resources;
  }

  @Input() set resources(value: { [key: string]: Resource | ResourceError }) {
    this._resources = value;
    if (
      !this.selectedValue ||
      (!Object.keys(value).includes(this.selectedValue) && this.selectedValue !== '___headers___')
    ) {
      this.selectedValue = Object.keys(value).length > 0 ? Object.keys(value)[0] : '___headers___';
    }
  }

  private _selectedValue: string | null = null;
  public set selectedValue(value: string | null) {
    this._selectedValue = value;
  }

  public get selectedValue(): string | null {
    return this._selectedValue;
  }

  get keys(): string[] {
    return Object.keys(this.resources);
  }

  private readonly navigation = inject(NavigationService);

  onDoubleClick(key: string) {
    this.navigation.navigateToId(this.resources[key]!.id);
  }

  async addItem() {
    const id = joinId(this.resourceId!, 'children');
    const newItem = await this.mainService.getNewItemData(id);
    if (newItem === null) return;
    this.emitNewChange({
      op: 'array_insert',
      id: id,
      index: this.keys.length,
      value: newItem,
    });
  }

  removeItem(index: number) {
    const key = this.keys[index];
    this.emitNewChange({
      op: 'bundle',
      changes: [
        {
          op: 'array_remove',
          timestamp: Date.now(),
          id: joinId(this.resourceId!, 'children'),
          index,
          oldValue: (this.resources[key] as Resource).data,
        },
        {
          op: 'array_remove',
          timestamp: Date.now(),
          id: joinId(this.resourceId!, 'aliases'),
          index: index,
          oldValue: key,
        },
      ],
    });
  }

  moveItemUp(index: number) {
    this.emitNewChange({
      op: 'array_swap',
      id: joinId(this.resourceId!, 'children'),
      indexA: index,
      indexB: index - 1,
    });
  }

  moveItemDown(index: number) {
    this.emitNewChange({
      op: 'array_swap',
      id: joinId(this.resourceId!, 'children'),
      indexA: index,
      indexB: index + 1,
    });
  }

  protected readonly joinId = joinId;
  protected readonly fileFormatIcon = fileFormatIcon;
}
