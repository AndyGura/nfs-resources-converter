import { ChangeDetectionStrategy, Component, Input } from '@angular/core';
import { NgxDeepEqualsPureService } from 'ngx-deep-equals-pure';
import { NavigationService } from '../../../../services/navigation.service';

@Component({
  selector: 'app-sidenav-res-list',
  templateUrl: './sidenav-res-list.component.html',
  styleUrls: ['./sidenav-res-list.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SidenavResListComponent {
  _resources: { [key: string]: BlockData | ReadError } = {};
  get resources(): { [key: string]: BlockData | ReadError } {
    return this._resources;
  }

  @Input() set resources(value: { [key: string]: BlockData | ReadError }) {
    const listUpdated = !this._resources || !this.deep.deepEquals(Object.keys(this._resources), Object.keys(value));
    this._resources = value;
    if (listUpdated) {
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

  constructor(private readonly deep: NgxDeepEqualsPureService, private readonly navigation: NavigationService) {}

  onDoubleClick(key: string) {
    this.navigation.navigateToId(this.resources[key]!.id);
  }
}
