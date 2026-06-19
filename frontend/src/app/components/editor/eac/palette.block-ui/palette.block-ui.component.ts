import { ChangeDetectionStrategy, Component, ElementRef, ViewChild } from '@angular/core';
import { SubscribableGuiComponent } from '../../gui.component';
import { joinId } from '../../../../utils/join-id';

@Component({
  selector: 'app-palette-block-ui',
  templateUrl: './palette.block-ui.component.html',
  styleUrls: ['./palette.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  standalone: false,
})
export class PaletteBlockUiComponent extends SubscribableGuiComponent {
  @ViewChild('colorInput') colorInput!: ElementRef<HTMLInputElement>;

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
    this.colorInput.nativeElement.value =
      '#' + this.lpad(this.resourceData.colors.data[this.selectedIndex].toString(16), '0', 8);
    this.colorInput.nativeElement.click();
  }

  onColorChange(hex: string | null) {
    if (!this.resourceId || !this.resourceData || this.selectedIndex === null) {
      this.selectedIndex = null;
      return;
    }
    const color = this.resourceData.colors.data[this.selectedIndex];
    const alpha = color & 0xff;
    const value = hex ? parseInt(hex.substring(1), 16) : 0;
    this.onValueSet((alpha | (value << 8)) >>> 0, 'colors', 'data', this.selectedIndex);
  }

  async addColor() {
    if (!this.resourceId || !this.resourceData) return;
    this.emitNewChange({
      id: joinId(this.resourceId!, 'colors', 'data'),
      op: 'array_insert',
      index: this.resourceData.colors.data.length,
      value: 0xff,
    });
  }

  removeLastColor() {
    if (!this.resourceId || !this.resourceData || this.resourceData.colors.data.length === 0) return;
    this.emitNewChange({
      id: joinId(this.resourceId!, 'colors', 'data'),
      op: 'array_remove',
      index: this.resourceData.colors.data.length - 1,
      oldValue: this.resourceData.colors.data[this.resourceData.colors.data.length - 1],
    });
  }
}
