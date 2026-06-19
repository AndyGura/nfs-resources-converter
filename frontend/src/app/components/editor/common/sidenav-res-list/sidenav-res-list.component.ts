import { ChangeDetectionStrategy, Component, Input } from '@angular/core';
import { NavigationService } from '../../../../services/navigation.service';
import { BlockData, ReadError } from '../../types';
import { joinId } from '../../../../utils/join-id';

@Component({
  selector: 'app-sidenav-res-list',
  templateUrl: './sidenav-res-list.component.html',
  styleUrls: ['./sidenav-res-list.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  standalone: false,
})
export class SidenavResListComponent {
  _resources: { [key: string]: BlockData | ReadError } = {};
  get resources(): { [key: string]: BlockData | ReadError } {
    return this._resources;
  }

  @Input() set resources(value: { [key: string]: BlockData | ReadError }) {
    this._resources = value;
    if (!this.selectedValue || !Object.keys(value).includes(this.selectedValue)) {
      this.selectedValue = Object.keys(value).length > 0 ? Object.keys(value)[0] : null;
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

  constructor(private readonly navigation: NavigationService) {}

  onDoubleClick(key: string) {
    this.navigation.navigateToId(this.resources[key]!.id);
  }

  protected readonly joinId = joinId;
}
