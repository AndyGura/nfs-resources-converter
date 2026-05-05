import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  EventEmitter,
  Input,
  Output,
  ViewChild
} from '@angular/core';
import { GuiComponentInterface } from '../../gui-component.interface';
import { NgxMatColorPickerComponent } from '@angular-material-components/color-picker/lib/components/color-picker/color-picker.component';
import { Color } from '@angular-material-components/color-picker';
import { GlobalPositionStrategy } from '@angular/cdk/overlay';
import { BlockData, Resource } from '../../types';
import { MainService } from '../../../../services/main.service';
import { joinId } from '../../../../utils/join-id';

@Component({
  selector: 'app-palette-block-ui',
  templateUrl: './palette.block-ui.component.html',
  styleUrls: ['./palette.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PaletteBlockUiComponent implements GuiComponentInterface {
  private _resource: Resource | null = null;

  @Input()
  set resource(value: Resource | null) {
    this._resource = value;
    this.cdr.markForCheck();
  }

  get resource(): Resource | null {
    return this._resource;
  }

  get resourceData(): BlockData | null {
    return this.resource?.data;
  }

  @Input() hideName: boolean = false;

  @Input() hideBlockActions: boolean = false;

  @Output('changed') changed: EventEmitter<void> = new EventEmitter<void>();

  @ViewChild('picker') picker!: NgxMatColorPickerComponent;

  constructor(
    private readonly mainService: MainService,
    private readonly cdr: ChangeDetectorRef,
  ) {}

  lpad(str: string, padString: string, length: number) {
    while (str.length < length) str = padString + str;
    return str;
  }

  private selectedIndex: number | null = null;

  onColorClicked(em: HTMLDivElement, index: number) {
    if (!this.resourceData) {
      this.selectedIndex = null;
      return;
    }
    this.selectedIndex = index;
    const color = this.resourceData.colors.data[index] || 0;
    this.picker.select(
      new Color((color & 0xff000000) >>> 24, (color & 0xff0000) >>> 16, (color & 0xff00) >>> 8, color & 0xff),
    );
    this.picker.open();
    const ps = new GlobalPositionStrategy();
    ps.top(Math.min(em.offsetTop, window.innerHeight - 450) + 'px');
    ps.left(Math.min(em.offsetLeft, window.innerWidth - 380) + 'px');
    this.picker._popupRef.updatePositionStrategy(ps);
    ps.apply();
  }

  onColorChange(color: Color | null) {
    if (!this.resource || !this.resourceData) {
      this.selectedIndex = null;
      return;
    }
    if (this.selectedIndex !== null) {
      const value = color ? parseInt(color.toHex8String().substring(1), 16) : 0;
      this.resourceData.colors.data[this.selectedIndex] = value;
      this.mainService.dataBlockChange$.next([joinId(this.resource.id, 'colors/data', this.selectedIndex), value]);
      this.cdr.markForCheck();
    }
  }

  async addColor() {
    if (!this.resource || !this.resourceData) return;
    this.resourceData.colors.data.push(0xff);
    this.mainService.dataBlockChange$.next([joinId(this.resource.id, 'colors/data'), this.resourceData.colors.data]);
    this.cdr.markForCheck();
  }

  removeLastColor() {
    if (!this.resource || !this.resourceData || this.resourceData.colors.data.length === 0) return;
    this.resourceData.colors.data.pop();
    this.mainService.dataBlockChange$.next([joinId(this.resource.id, 'colors/data'), this.resourceData.colors.data]);
    this.cdr.markForCheck();
  }
}
