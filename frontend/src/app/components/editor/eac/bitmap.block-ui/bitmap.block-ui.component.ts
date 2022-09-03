import { ChangeDetectionStrategy, ChangeDetectorRef, Component, NgZone } from '@angular/core';
import { GuiComponentInterface } from '../../gui-component.interface';
import { EelDelegateService } from '../../../../services/eel-delegate.service';
import { intArrayToBitmap } from '../../../../utils/int-array-to-bitmap';

@Component({
  selector: 'app-bitmap.block-ui',
  templateUrl: './bitmap.block-ui.component.html',
  styleUrls: ['./bitmap.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BitmapBlockUiComponent implements GuiComponentInterface {

  private _resourceData: ReadData | null = null;
  get resourceData(): ReadData | null {
    return this._resourceData;
  }
  set resourceData(value: ReadData | null) {
    this._resourceData = value;
    if (this.resourceData) {
      this.updateImageSource().then();
    }
  }

  imageSource: string | undefined;
  name: string = '';
  hasSerializedFile: boolean = false;

  constructor(
    private readonly eelDelegate: EelDelegateService,
    private readonly cdr: ChangeDetectorRef,
  ) { }

  async updateImageSource(): Promise<void> {
    let pixels = this.resourceData?.value?.bitmap?.value;
    if (this.resourceData?.block_class_mro?.startsWith('Bitmap8Bit')) {
      const palette = await this.eelDelegate.determine8BitBitmapPalette(this.resourceData?.block_state?.id);
      // TODO link to palette if in the same file: when adding editing tool, bitmap should be updated
      if (palette) {
        pixels = pixels.map((x: number) => palette?.value?.colors?.value[x].value);
      } else {
        pixels = pixels.map((x: number) => (x << 24) | (x << 16) | (x << 8) | x);
      }
    }
    this.imageSource = intArrayToBitmap(pixels,
      this.resourceData?.value?.width?.value,
      this.resourceData?.value?.height?.value);
    this.cdr.markForCheck();
  }

  async openResourceInSystem(): Promise<void> {
    if (!this.resourceData) {
      console.error('Cannot open. Resource data is empty')
      return;
    }
    await this.eelDelegate.serializeResource(this.resourceData.block_state.id);
    this.hasSerializedFile = true;
    this.cdr.markForCheck();
  }

  async pullResource(): Promise<void> {
    await this.eelDelegate.deserializeResource(this.resourceData?.block_state.id);
    this.hasSerializedFile = false;
    this.cdr.markForCheck();
  }

}
