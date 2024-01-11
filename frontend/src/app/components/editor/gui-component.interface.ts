import { EventEmitter } from '@angular/core';

export interface GuiComponentInterface {
  resource: Resource | null;

  changed: EventEmitter<void>;
}
