import { Injectable, NgZone } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

declare const eel: { expose: (func: Function, alias: string) => void } & { [key: string]: Function };

@Injectable({
  providedIn: 'root'
})
export class EelDelegateService {

  public readonly openedResource$: BehaviorSubject<ReadData | null> = new BehaviorSubject<ReadData | null>(null);

  constructor(
    private readonly ngZone: NgZone,
  ) {
    eel.expose(this.wrapHandler(this.openFile), 'open_file');
    eel['on_angular_ready']();
  }

  private wrapHandler(handler: (...args: any[]) => unknown) {
    return ((...args: any[]) => {
      try {
        NgZone.assertInAngularZone();
        handler.bind(this)(...args);
      } catch (err) {
        this.ngZone.run(handler, this, args);
      }
    });
  }

  public async openFile(path: string) {
    const res: ReadData = await eel['open_file'](path)();
    this.openedResource$.next(res);
  }

  public async determine8BitBitmapPalette(bitmapId: string): Promise<ReadData | null> {
    return eel['determine_8_bit_bitmap_palette'](bitmapId)();
  }
}
