import { EventEmitter } from '@angular/core';

export interface GuiComponentInterface {

  resourceData: ReadData | null;
  name: string;

  changed: EventEmitter<void>;

}
