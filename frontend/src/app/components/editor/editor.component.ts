import { ChangeDetectionStrategy, Component, Input, ViewChild } from '@angular/core';
import { EelDelegateService } from '../../services/eel-delegate.service';
import { DataBlockUIDirective } from './data-block-ui.directive';
import { FallbackBlockUiComponent } from './fallback.block-ui/fallback.block-ui.component';

@Component({
  selector: 'app-editor',
  templateUrl: './editor.component.html',
  styleUrls: ['./editor.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EditorComponent {

  @ViewChild(DataBlockUIDirective, { static: true }) dataBlockUiHost!: DataBlockUIDirective;

  private _resourceData: ReadData | null = null;
  public get resourceData(): ReadData | null {
    return this._resourceData;
  }

  @Input()
  public set resourceData(value: ReadData | null) {
    this._resourceData = value;
    this.dataBlockUiHost.viewContainerRef.clear();
    if (this._resourceData) {
      const component = FallbackBlockUiComponent;
      const componentRef = this.dataBlockUiHost.viewContainerRef.createComponent(component);
      componentRef.instance.resourceData = this.resourceData;
    }
  };

  constructor(readonly eelDelegate: EelDelegateService) {
  }

}
